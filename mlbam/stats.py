"""
Future: parse https://statsapi.web.nhl.com/api/v1/standings

Help: see https://github.com/dword4/nhlapi#standing
"""

import logging
import os
import requests
import sys

import mlbam.auth as auth
import mlbam.util as util
import mlbam.config as config


LOG = logging.getLogger(__name__)

STANDINGS_URL = 'https://statsapi.web.nhl.com/api/v1/standings'

# from https://statsapi.web.nhl.com/api/v1/standings'
STANDINGS_TYPES = ('regularSeason', 'wildCard', 'divisionLeaders', 'wildCardWithLeaders',
                   'preseason', 'postseason', 'byDivision', 'byConference', 'byLeague',)

STANDINGS_OPTIONS = ('all', 'division', 'conference', 'wildcard', 'league', 'postseason', 'preseason')

TEAMS_TO_FAVS = {
    'Nashville Predators': 'nsh', 'Boston Bruins': 'bos', 'Tampa Bay Lightning': 'tbl',
    'Vegas Golden Knights': 'vgk', 'Winnipeg Jets': 'wpg', 'Toronto Maple Leafs': 'tor',
    'Washington Capitals': 'wsh', 'San Jose Sharks': 'sjs', 'Minnesota Wild': 'min',
    'Pittsburgh Penguins': 'pit', 'Los Angeles Kings': 'lak', 'Columbus Blue Jackets': 'cbj',
    'Anaheim Ducks': 'ana', 'St. Louis Blues': 'stl', 'Colorado Avalanche': 'col',
    'Philadelphia Flyers': 'phi', 'New Jersey Devils': 'njd', 'Dallas Stars': 'dal',
    'Florida Panthers': 'fla', 'Calgary Flames': 'cgy', 'Carolina Hurricanes': 'car',
    'New York Rangers': 'nyr', 'Chicago Blackhawks': 'chi', 'Edmonton Oilers': 'edm',
    'New York Islanders': 'nyi', 'Detroit Red Wings': 'det', 'Vancouver Canucks': 'van',
    'Montréal Canadiens': 'mtl', 'Arizona Coyotes': 'ari', 'Ottawa Senators': 'ott',
    'Buffalo Sabres': 'buf',
}


def _is_fav(long_team_name):
    return TEAMS_TO_FAVS[long_team_name] in util.get_csv_list(config.CONFIG.parser['favs'])


def _match(input_option, full_option, min_chars=2):
    num_chars = len(input_option)
    return input_option[:num_chars] == full_option[:num_chars]


def get_standings(standings_option='all'):
    if _match(standings_option, 'all') or _match(standings_option, 'division'):
        display_standings('byDivision', 'Division')
    if _match(standings_option, 'all') or _match(standings_option, 'conference'):
        display_standings('byConference', 'Conference', rank_tag='conferenceRank')
    if _match(standings_option, 'all') or _match(standings_option, 'wildcard'):
        display_standings('wildCard', 'Wildcard', rank_tag='wildCardRank')
    if _match(standings_option, 'all') or _match(standings_option, 'overall') or _match(standings_option, 'league'):
        display_standings('byLeague', 'League', rank_tag='leagueRank')

    if _match(standings_option, 'playoff') or _match(standings_option, 'postseason'):
        display_standings('postseason', 'Playoffs')
    if _match(standings_option, 'preseason'):
        display_standings('preseason', 'Preseason')


def display_standings(standings_type='division', display_title='', rank_tag='divisionRank'):
    headers = {
        'User-Agent': config.CONFIG.ua_iphone,
        'Connection': 'close'
    }
    url = '{}/{}'.format(STANDINGS_URL, standings_type)
    util.log_http(url, 'get', headers, sys._getframe().f_code.co_name)
    resp = requests.get(url, headers=headers, cookies=auth.load_cookies(), verify=config.VERIFY_SSL)

    json_file = os.path.join(config.CONFIG.dir, 'standings.json')
    with open(json_file, 'w') as f:  # write date to json_file
        f.write(resp.text)

    # with open(json_file) as games_file:
    #     json_data = json.load(games_file)
    json_data = resp.json()

    # import pprint
    # pprint.pprint(json_data)

    outl = list()
    if display_title != '':
        outl.append('   ========  {}  ========'.format(display_title))
    needs_line_hr = False
    for record in json_data['records']:
        if standings_type == record['standingsType']:
            if needs_line_hr > 0:
                pass
                # outl.append('-' * 10)
            header = ''
            for tag in ('conference', 'division'):
                if tag in record:
                    if 'name' in record[tag]:
                        header = _add_to_header(header, record[tag]['name'])
                    else:
                        header = _add_to_header(header, record[tag])
            if header:
                header = '--- ' + header + ' ---'
                outl.append('   {}'.format(header))
                needs_line_hr = True
        else:
            LOG.error('Unexpected: standingsType=%s, not %s', record['standingsType'], standings_type)
        for teamrec in record['teamRecords']:
            clinch = ''
            if 'clinchIndicator' in teamrec:
                clinch = teamrec['clinchIndicator'] + '-'
            rank = ''
            if rank_tag in teamrec:
                rank = teamrec[rank_tag]
            color_on = ''
            color_off = ''
            if _is_fav(teamrec['team']['name']):
                if config.CONFIG.parser['fav_colour'] != '':
                    color_on = util.fg_ansi_colour(config.CONFIG.parser['fav_colour'])
                    color_off = util.ANSI_CONTROL_CODES['reset']
            outl.append('{color_on}{rank:2} {clinch}{name:22}\t{win:2} {ot:2} {loss:2} {point:3} [{streak}]{color_off}'
                        .format(color_on=color_on, rank=rank, clinch=clinch, name=teamrec['team']['name'],
                                win=teamrec['leagueRecord']['wins'], ot=teamrec['leagueRecord']['ot'],
                                loss=teamrec['leagueRecord']['losses'], point=teamrec['points'],
                                streak=teamrec['streak']['streakCode'], color_off=color_off))
    print('\n'.join(outl))


def _add_to_header(header, text):
    if header:
        return header + ' - ' + text
    return text
