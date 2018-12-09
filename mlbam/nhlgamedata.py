"""
Models the game data retrieved via JSON.
"""

import logging
import os
import time

from datetime import datetime
from datetime import timedelta

import mlbam.common.config as config
import mlbam.common.gamedata as gamedata
import mlbam.common.util as util
import mlbam.common.displayutil as displayutil

from mlbam.common.displayutil import ANSI


LOG = logging.getLogger(__name__)


TEAM_CODES = ('ana', 'ari', 'bos', 'buf', 'car', 'cbj', 'cgy', 'chi', 'col', 'dal', 'det', 'edm', 'fla', 'lak',
              'min', 'mtl', 'njd', 'nsh', 'nyi', 'nyr', 'ott', 'phi', 'pit', 'sjs', 'stl', 'tbl', 'tor', 'van',
              'vgk', 'wpg', 'wsh')


FILTERS = {
    'favs': '',  # is filled out by config parser
    'metropolitan': 'car,cbj,njd,nyi,nyr,phi,pit,wsh',
    'atlantic': 'bos,buf,det,fla,mtl,ott,tbl,tor',
    'central': 'chi,col,dal,min,nsh,stl,wpg',
    'pacific': 'ana,ari,cgy,edm,lak,sjs,van,vgk'
}
FILTERS['east'] = '{},{}'.format(FILTERS['metropolitan'], FILTERS['atlantic'])
FILTERS['west'] = '{},{}'.format(FILTERS['central'], FILTERS['pacific'])

# this map is used to transform the statsweb feed name to something shorter
FEEDTYPE_MAP = {
    'away': 'a',
    'home': 'h',
    'french': 'fr',
    'national': 'nat',
    'condensed': 'cnd',
    'recap': 'rcp',
    'audio-away': 'aud-a',
    'audio-home': 'aud-h',
}


class GameDataRetriever:
    """Retrieves and parses game data from statsapi.mlb.com"""

    @staticmethod
    def _get_games_by_date(date_str=None):
        if date_str is None:
            date_str = time.strftime("%Y-%m-%d")
        if config.SAVE_JSON_FILE_BY_TIMESTAMP:
            json_file = os.path.join(config.CONFIG.dir, 'gamedata-{}.json'.format(time.strftime("%Y-%m-%d-%H%M")))
        else:
            json_file = os.path.join(config.CONFIG.dir, 'gamedata.json')
        LOG.debug('Getting game data...')

        url = ('{0}/schedule?&startDate={1}&endDate={1}&expand='
               'schedule.teams,schedule.linescore,schedule.game.content.media.epg').format(config.CONFIG.parser['api_url'],
                                                                                           date_str)
        json_data = util.request_json(url, 'gamedata')

        game_records = dict()  # we return this dictionary

        if json_data is None:
            LOG.error("No JSON data returned for %s", date_str)
            return None
        if json_data['dates'] is None or len(json_data['dates']) < 1:
            LOG.debug("_get_games_by_date: no game data for %s", date_str)
            return None

        for game in json_data['dates'][0]['games']:
            # LOG.debug('game: {}'.format(game))
            game_pk_str = str(game['gamePk'])
            game_records[game_pk_str] = dict()
            game_rec = game_records[game_pk_str]
            game_rec['game_pk'] = game_pk_str
            game_rec['abstractGameState'] = str(game['status']['abstractGameState'])  # Preview, Live, Final
            game_rec['detailedState'] = str(game['status']['detailedState'])  # is something like: Scheduled, Live, Final, In Progress, Critical
            game_rec['nhldate'] = datetime.strptime(str(game['gameDate']), "%Y-%m-%dT%H:%M:%SZ")
            game_rec['away'] = dict()
            game_rec['away']['name'] = str(game['teams']['away']['team']['name'])
            game_rec['away']['abbrev'] = str(game['teams']['away']['team']['abbreviation'].lower())
            game_rec['away']['score'] = str(game['teams']['away']['score'])
            game_rec['home'] = dict()
            game_rec['home']['name'] = str(game['teams']['home']['team']['name'])
            game_rec['home']['abbrev'] = str(game['teams']['home']['team']['abbreviation'].lower())
            game_rec['home']['score'] = str(game['teams']['home']['score'])
            game_rec['favourite'] = gamedata.is_fav(game_rec)
            # game_rec['nhltv_link'] = 'http://nhl.com/tv/{0}/'.format(game_pk_str)

            # linescore
            game_rec['linescore'] = dict()
            game_rec['linescore']['currentPeriod'] = str(game['linescore']['currentPeriod'])
            if 'currentPeriodOrdinal' in game['linescore']:
                game_rec['linescore']['currentPeriodOrdinal'] = str(game['linescore']['currentPeriodOrdinal'])  # : "2nd", "OT", "SO"
                game_rec['linescore']['currentPeriodTimeRemaining'] = str(game['linescore']['currentPeriodTimeRemaining'])  # : "18:58", "Final"
                game_rec['linescore']['hasShootout'] = bool(game['linescore']['hasShootout'])
            else:
                game_rec['linescore']['currentPeriodOrdinal'] = 'Not Started'
                game_rec['linescore']['currentPeriodTimeRemaining'] = '20:00'
                game_rec['linescore']['hasShootout'] = False

            # epg
            game_rec['feed'] = dict()
            if 'media' in game['content'] and 'epg' in game['content']['media']:
                for media in game['content']['media']['epg']:
                    if media['title'] == 'NHLTV':
                        for stream in media['items']:
                            if stream['mediaFeedType'] != 'COMPOSITE' and stream['mediaFeedType'] != 'ISO':
                                feedtype = str(stream['mediaFeedType']).lower()  # home, away, national, french, ...
                                game_rec['feed'][feedtype] = dict()
                                game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaPlaybackId'])
                                game_rec['feed'][feedtype]['eventId'] = str(stream['eventId'])
                                game_rec['feed'][feedtype]['callLetters'] = str(stream['callLetters'])
                    elif media['title'] == 'Extended Highlights':
                        feedtype = 'condensed'
                        if len(media['items']) > 0:
                            game_rec['feed'][feedtype] = dict()
                            stream = media['items'][0]
                            game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaPlaybackId'])
                            for playback_item in stream['playbacks']:
                                if playback_item['name'] == config.CONFIG.playback_scenario:
                                    game_rec['feed'][feedtype]['playback_url'] = playback_item['url']
                    elif media['title'] == 'Recap':
                        feedtype = 'recap'
                        if len(media['items']) > 0:
                            game_rec['feed'][feedtype] = dict()
                            stream = media['items'][0]
                            game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaPlaybackId'])
                            for playback_item in stream['playbacks']:
                                if playback_item['name'] == config.CONFIG.playback_scenario:
                                    game_rec['feed'][feedtype]['playback_url'] = playback_item['url']
                    elif media['title'] == 'Audio':
                        for stream in media['items']:
                            feedtype = 'audio-' + str(stream['mediaFeedType']).lower()  # home, away, national, french, ...
                            game_rec['feed'][feedtype] = dict()
                            game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaPlaybackId'])
                            game_rec['feed'][feedtype]['eventId'] = str(stream['eventId'])
                            game_rec['feed'][feedtype]['callLetters'] = str(stream['callLetters'])
        return game_records

    def process_game_data(self, game_date, num_days=1):
        game_days_list = list()
        for i in range(0, num_days):
            game_records = self._get_games_by_date(game_date)
            if game_records is not None:
                game_days_list.append((game_date, game_records))
            game_date = datetime.strftime(datetime.strptime(game_date, "%Y-%m-%d") + timedelta(days=1), "%Y-%m-%d")
        return game_days_list


class GameDatePresenter:
    """Formats game data for CLI output."""

    def __get_feeds_for_display(self, game_rec):
        non_highlight_feeds = list()
        use_short_feeds = config.CONFIG.parser.getboolean('use_short_feeds', True)
        for feed in sorted(game_rec['feed'].keys()):
            if feed not in config.HIGHLIGHT_FEEDTYPES and not feed.startswith('audio-'):
                if use_short_feeds:
                    non_highlight_feeds.append(gamedata.convert_feedtype_to_short(feed, FEEDTYPE_MAP))
                else:
                    non_highlight_feeds.append(feed)
        highlight_feeds = list()
        for feed in game_rec['feed'].keys():
            if feed in config.HIGHLIGHT_FEEDTYPES and not feed.startswith('audio-'):
                if use_short_feeds:
                    highlight_feeds.append(gamedata.convert_feedtype_to_short(feed, FEEDTYPE_MAP))
                else:
                    highlight_feeds.append(feed)
        return '{:7} {}'.format('/'.join(non_highlight_feeds), '/'.join(highlight_feeds))


    def display_game_data(self, game_date, game_records, arg_filter):
        show_scores = config.CONFIG.parser.getboolean('scores')
        border = displayutil.Border(use_unicode=config.UNICODE)
        if game_records is None:
            # outl.append("No game data for {}".format(game_date))
            LOG.info("No game data for {}".format(game_date))
            # LOG.info("No game data to display")
            return

        outl = list()  # holds list of strings for output
        print_outl = False

        # print header
        date_hdr = '{:7}{} {}'.format('', game_date, datetime.strftime(datetime.strptime(game_date, "%Y-%m-%d"), "%a"))
        if show_scores:
            outl.append("{:64} {pipe} {:^5} {pipe} {:^9} {pipe} {}"
                        .format(date_hdr, 'Score', 'State', 'Feeds', pipe=border.pipe))
            outl.append("{c_on}{}{pipe}{}{pipe}{}{pipe}{}{c_off}"
                        .format(border.thickdash * 65, border.thickdash * 7, border.thickdash * 11, border.thickdash * 14,
                                pipe=border.junction, c_on=border.border_color, c_off=border.color_off))
        else:
            outl.append("{:64} {pipe} {:^9} {pipe} {}".format(date_hdr, 'State', 'Feeds', pipe=border.pipe))
            outl.append("{c_on}{}{pipe}{}{pipe}{}{c_off}"
                        .format(border.thickdash * 65, border.thickdash * 11, border.thickdash * 14,
                                pipe=border.junction, c_on=border.border_color, c_off=border.color_off))

        games_displayed_count = 0
        for game_pk in game_records:
            if gamedata.apply_filter(game_records[game_pk], arg_filter, FILTERS) is not None:
                games_displayed_count += 1
                outl.extend(self._display_game_details(game_pk, game_records[game_pk], games_displayed_count))
                print_outl = True

        if print_outl:
            print('\n'.join(outl))

    def _display_game_details(self, game_pk, game_rec, games_displayed_count):
        outl = list()
        border = displayutil.Border(use_unicode=config.UNICODE)
        color_on = ''
        color_off = ''
        if gamedata.is_fav(game_rec):
            if config.CONFIG.parser['fav_colour'] != '':
                color_on = ANSI.fg(config.CONFIG.parser['fav_colour'])
                color_off = ANSI.reset()
        if game_rec['abstractGameState'] == 'Live':
            color_on += ANSI.control_code('bold')
            color_off = ANSI.reset()
        show_scores = config.CONFIG.parser.getboolean('scores')
        game_info_str = "{}: {} ({}) at {} ({})".format(util.convert_time_to_local(game_rec['nhldate']),
                                                        game_rec['away']['name'], game_rec['away']['abbrev'].upper(),
                                                        game_rec['home']['name'], game_rec['home']['abbrev'].upper())
        game_state = ''
        game_state_color_on = color_on
        game_state_color_off = color_off
        if game_rec['abstractGameState'] not in ('Preview', ):
            if not show_scores:
                game_state = game_rec['abstractGameState']
                if 'In Progress - ' in game_rec['detailedState']:
                    game_state = game_rec['detailedState'].split('In Progress - ')[-1]
                elif game_rec['detailedState'] not in ('Live', 'Final', 'Scheduled', 'In Progress'):
                    game_state = game_rec['detailedState']
            else:
                if 'Critical' in game_rec['detailedState']:
                    game_state_color_on = ANSI.fg(config.CONFIG.parser['game_critical_colour'])
                    game_state_color_off = ANSI.reset()
                if game_rec['linescore']['currentPeriodTimeRemaining'] == 'Final' \
                        and game_rec['linescore']['currentPeriodOrdinal'] == '3rd':
                    game_state = 'Final'
                else:
                    game_state = '{} {}'.format(game_rec['linescore']['currentPeriodTimeRemaining'].title(),
                                                game_rec['linescore']['currentPeriodOrdinal'])
        # else:
        #    game_state = 'Pending'
        if config.CONFIG.parser.getboolean('scores'):
            score = ''
            if game_rec['abstractGameState'] not in ('Preview', ):
                score = '{}-{}'.format(game_rec['away']['score'], game_rec['home']['score'])
            outl.append("{c_on}{gameinfo:<64}{c_off} {pipe} {c_on}{score:^5}{c_off} {pipe} {gsc_on}{state:>9}{gsc_off} {pipe} {c_on}{feeds}{c_off}"
                        .format(gameinfo=game_info_str, score=score, state=game_state,
                                gsc_on=game_state_color_on, gsc_off=game_state_color_off, feeds=self.__get_feeds_for_display(game_rec),
                                pipe=border.pipe, c_on=color_on, c_off=color_off))
        else:
            outl.append("{c_on}{gameinfo:<64}{c_off} {pipe} {c_on}{state:^9}{c_off} {pipe} {c_on}{feeds}{c_off}"
                        .format(gameinfo=game_info_str, state=game_state, feeds=self.__get_feeds_for_display(game_rec),
                                pipe=border.pipe, c_on=color_on, c_off=color_off))
        if config.CONFIG.parser.getboolean('debug') and config.CONFIG.parser.getboolean('verbose'):
            for feedtype in game_rec['feed']:
                outl.append('    {}: {}  [game_pk:{}, mediaPlaybackId:{}]'.format(feedtype,
                                                                                  game_rec['abstractGameState'],
                                                                                  game_pk,
                                                                                  game_rec['feed'][feedtype]['mediaPlaybackId']))
        return outl

    def get_audio_stream_url(self):
        # http://hlsaudio-akc.med2.med.nhl.com/ls04/nhl/2017/12/31/NHL_GAME_AUDIO_TORVGK_M2_VISIT_20171231_1513799214035/master_radio.m3u8
        pass


