#!/usr/bin/env python
"""
This project provides a CLI interface into streaming NHL games from NHL.tv.

Includes code borrowed and modified from the following projects:

- https://github.com/eracknaphobia/plugin.video.nhlgcl (Kodi plugin)
- https://github.com/NHLGames/nhl.py

"""

import argparse
import inspect
import json
import logging
import os
import requests
import subprocess
import sys
import time

from datetime import datetime
from datetime import timedelta

import mlbam.common.config as config
import mlbam.common.gamedata as gamedata
import mlbam.common.util as util
import mlbam.auth as auth
import mlbam.nhlconfig as nhlconfig
import mlbam.nhlgamedata as nhlgamedata
import mlbam.standings as standings
import mlbam.nhlstream as nhlstream


LOG = None  # initialized in init_logging


HELP_HEADER = """NHL game tracker and stream viewer.
"""
HELP_FOOTER = """Use --usage for full usage instructions and pre-requisites.

Filters:
    For the --filter option use either the built-in filters (see --list-filters) or
    provide your own list of teams, separated by comma: e.g. tor,bos,nyy

Feed Identifiers:
    You can use either the short form feed identifier or the long form:
    {feedhelp}""".format(feedhelp=gamedata.get_feedtype_keystring(nhlgamedata.FEEDTYPE_MAP))


def display_usage():
    """Displays contents of readme file."""
    current_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
    readme_path = os.path.abspath(os.path.join(current_dir, '..', 'README.md'))
    if not os.path.exists(readme_path):
        print("Could not find documentation file [expected at: {}]".format(readme_path))
        return -1
    if 'PAGER' in os.environ:
        cmd = [os.environ['PAGER'], readme_path]
        subprocess.run(cmd)
    else:
        with open(readme_path, 'r') as infile:
            for line in infile:
                print(line, end='')
    return 0


def main(argv=None):
    """Entry point for mlbv"""

    # using argparse (2.7+) https://docs.python.org/2/library/argparse.html
    parser = argparse.ArgumentParser(description=HELP_HEADER, epilog=HELP_FOOTER,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init", action="store_true",
                        help="Generates a config file using a combination of defaults plus prompting for NHL.tv credentials.")
    parser.add_argument("--usage", action="store_true", help="Display full usage help.")
    parser.add_argument("-d", "--date", help="Display games/standings for date. Format: yyyy-mm-dd")
    parser.add_argument("--days", type=int, default=1, help="Number of days to display")
    parser.add_argument("--tomorrow", action="store_true", help="Use tomorrow's date")
    parser.add_argument("--yesterday", action="store_true", help="Use yesterday's date")
    parser.add_argument("-t", "--team",
                        help="Play selected game feed for team, one of: {}".format(nhlgamedata.TEAM_CODES))
    parser.add_argument("-f", "--feed",
                        help=("Feed type, either a live/archive game feed or highlight feed "
                              "(if available). Available feeds are shown in game list,"
                              "and have a short form and long form (see 'Feed identifiers' section below)"))
    parser.add_argument("-r", "--resolution",
                        help=("Stream resolution for streamlink (overrides settting in config file). "
                              "Choices: {}. Can also be a comma-separated list of values (no spaces), "
                              "e.g 720p_alt,720p,540p").format(config.BANDWIDTH_CHOICES))
    parser.add_argument("--from-start", action="store_true", help="Start live/archive stream from beginning")
    parser.add_argument("--offset", help=("Format: HH:MM:SS. "
                                          "For live games: this is the amount of time to rewind from now. "
                                          "For archived games: the amount of time to skip from the beginning of the stream. "
                                          "e.g. 01:00:00 will start an archived game one hour from the beginning, "
                                          "or will start a live game one hour prior to now."))
    parser.add_argument("--duration", help="Limit the playback duration, useful for watching segments of a stream")
    parser.add_argument("--favs", help=argparse.SUPPRESS)
                        # help=("Favourite teams, a comma-separated list of favourite teams " "(normally specified in config file)"))
    parser.add_argument("-o", "--filter", nargs='?', const='favs', metavar='filtername|teams',
                        help=("Filter output. Either a filter name (see --list-filters) or a comma-separated "
                              "list of team codes, eg: 'tor.bos,wsh'. Default: favs"))
    parser.add_argument("--list-filters", action='store_true', help="List the built-in filters")
    parser.add_argument("-s", "--scores", action="store_true",
                        help="Show scores (default off; overrides config file)")
    parser.add_argument("-n", "--no-scores", action="store_true",
                        help="Do not show scores (default on; overrides config file)")
    parser.add_argument("--username", help=argparse.SUPPRESS)  # help="NHL.tv username. Required for live/archived games.")
    parser.add_argument("--password", help=argparse.SUPPRESS)  # help="NHL.tv password. Required for live/archived games.")
    parser.add_argument("--use-rogers", help="Use rogers form of NHL.tv authentication")
    parser.add_argument("--fetch", "--record", action="store_true", help="Save stream to file instead of playing")
    parser.add_argument("--wait", action="store_true",
                        help=("Wait for game to start (live games only). Will block launching the player until game time. "
                              "Useful when combined with the --fetch option."))
    parser.add_argument("--standings", nargs='?', const='division', metavar='category',
                        help=("[category] is one of: '" + ', '.join(standings.STANDINGS_OPTIONS) + "' [default: %(default)s]. "
                              "Display standings. This option will display selected standings category, then exit. "
                              "The standings category can be shortened down to one character (all matching "
                              "categories will be included), e.g. 'div'. "
                              "Can be combined with -d/--date option to show standings for any given date.")
                        )
    parser.add_argument("--recaps", nargs='?', const='all', metavar='FILTER',
                        help=("Play recaps for given teams. "
                              "[FILTER] is an optional filter as per --filter option"))
    parser.add_argument("-v", "--verbose", action="store_true", help=argparse.SUPPRESS)  # help="Increase output verbosity")
    parser.add_argument("-D", "--debug", action="store_true", help=argparse.SUPPRESS)    # help="Turn on debug output")
    args = parser.parse_args()

    if args.usage:
        return display_usage()

    team_to_play = None
    feedtype = None

    if args.init:
        return config.Config.generate_config(args.username, args.password, "NHL.tv")

    # get our config
    config.CONFIG = config.Config(nhlconfig.DEFAULTS, args)

    # append log files if DEBUG is set (from top of file)
    util.init_logging(os.path.join(config.CONFIG.dir,
                                   os.path.splitext(os.path.basename(sys.argv[0]))[0] + '.log'), True)

    global LOG
    LOG = logging.getLogger(__name__)

    if args.list_filters:
        print('List of built filters: ' + ', '.join(sorted(nhlgamedata.FILTERS.keys())))
        return 0
    if args.debug:
        config.CONFIG.parser['debug'] = 'true'
    if args.verbose:
        config.CONFIG.parser['verbose'] = 'true'
    if args.username:
        config.CONFIG.parser['username'] = args.username
    if args.password:
        config.CONFIG.parser['password'] = args.password
    if args.team:
        team_to_play = args.team.lower()
        if team_to_play not in nhlgamedata.TEAM_CODES:
            # Issue #4 all-star game has funky team codes
            LOG.warning('Unexpected team code: %s', team_to_play)
    if args.feed:
        feedtype = gamedata.convert_to_long_feedtype(args.feed.lower(), nhlgamedata.FEEDTYPE_MAP)
    if args.resolution:
        config.CONFIG.parser['resolution'] = args.resolution
    if args.scores:
        config.CONFIG.parser['scores'] = 'true'
    elif args.no_scores:
        config.CONFIG.parser['scores'] = 'false'
    if args.favs:
        config.CONFIG.parser['favs'] = args.favs
    if args.filter:
        config.CONFIG.parser['filter'] = args.filter

    if args.yesterday:
        args.date = datetime.strftime(datetime.today() - timedelta(days=1), "%Y-%m-%d")
    elif args.tomorrow:
        args.date = datetime.strftime(datetime.today() + timedelta(days=1), "%Y-%m-%d")
    elif args.date is None:
        args.date = datetime.strftime(datetime.today(), "%Y-%m-%d")

    if args.from_start and args.offset:
        LOG.error("ERROR: You cannot combine the '--from-start' and '--offset' options")
        return -1

    if args.standings:
        standings.get_standings(args.standings, args.date)
        return 0

    gamedata_retriever = nhlgamedata.GameDataRetriever()

    # retrieve all games for the dates given
    game_day_tuple_list = gamedata_retriever.process_game_data(args.date, args.days)

    if team_to_play is None and not args.recaps:
        # nothing to play; display the games
        presenter = nhlgamedata.GameDatePresenter()
        displayed_count = 0
        for game_date, game_records in game_day_tuple_list:
            presenter.display_game_data(game_date, game_records, args.filter)
            displayed_count += 1
            if displayed_count < len(game_day_tuple_list):
                print('')
        return 0

    # from this point we only care about first day in list
    if len(game_day_tuple_list) > 0:
        game_date, game_data = game_day_tuple_list[0]
    else:
        return 0  # nothing to stream

    if args.recaps:
        recap_teams = list()
        if args.recaps == 'all':
            for game_pk in game_data:
                # add the home team
                recap_teams.append(game_data[game_pk]['home']['abbrev'])
        else:
            for team in args.recaps.split(','):
                recap_teams.append(team.strip())
        for game_pk in game_data:
            game_rec = gamedata.apply_filter(game_data[game_pk], args.filter, nhlgamedata.FILTERS)
            if game_rec and (game_rec['home']['abbrev'] in recap_teams or game_rec['away']['abbrev'] in recap_teams):
                if 'recap' in game_rec['feed']:
                    LOG.info("Playing recap for %s at %s", game_rec['away']['abbrev'].upper(), game_rec['home']['abbrev'].upper())
                    stream_game_rec = nhlstream.get_game_rec(game_data, game_rec['home']['abbrev'])
                    nhlstream.play_stream(stream_game_rec, game_rec['home']['abbrev'], 'recap', game_date,
                                          args.fetch, None, None, offset=args.offset, duration=args.duration, is_multi_highlight=True)
                else:
                    LOG.info("No recap available for %s at %s", game_rec['away']['abbrev'].upper(), game_rec['home']['abbrev'].upper())
        return 0

    game_rec = nhlstream.get_game_rec(game_data, team_to_play)

    if args.wait and not util.has_reached_time(game_rec['nhldate']):
        LOG.info('Waiting for game to start. Local start time is %s', util.convert_time_to_local(game_rec['nhldate']))
        print('Use Ctrl-c to quit .', end='', flush=True)
        count = 0
        while not util.has_reached_time(game_rec['nhldate']):
            time.sleep(10)
            count += 1
            if count % 6 == 0:
                print('.', end='', flush=True)

        # refresh the game data
        LOG.info('Game time. Refreshing game data after wait...')
        game_day_tuple_list = gamedata_retriever.process_game_data(args.date, 1)
        if len(game_day_tuple_list) > 0:
            game_date, game_data = game_day_tuple_list[0]
        else:
            LOG.error('Unexpected error: no game data found after refresh on wait')
            return 0

        game_rec = nhlstream.get_game_rec(game_data, team_to_play)

    return nhlstream.play_stream(game_rec, team_to_play, feedtype, args.date, args.fetch,
                                 auth.nhl_login, args.from_start, offset=args.offset, duration=args.duration)


if __name__ == "__main__" or __name__ == "main":
    sys.exit(main())
