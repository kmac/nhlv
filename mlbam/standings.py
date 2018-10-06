"""
Future: parse https://statsapi.web.nhl.com/api/v1/standings

Help: see https://github.com/dword4/nhlapi#standing
"""

import logging
import os
import sys
import time

import mlbam.common.displayutil as displayutil
import mlbam.common.util as util
import mlbam.common.config as config

from mlbam.common.displayutil import ANSI


LOG = logging.getLogger(__name__)

STANDINGS_URL = 'https://statsapi.web.nhl.com/api/v1/standings/{standings_type}?date={date}'

# from https://statsapi.web.nhl.com/api/v1/standings?date={date}'
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
    if long_team_name in TEAMS_TO_FAVS.keys():
        return TEAMS_TO_FAVS[long_team_name] in util.get_csv_list(config.CONFIG.parser['favs'])
    return False


def _match(input_option, full_option, min_chars=2):
    num_chars = len(input_option)
    return input_option[:num_chars] == full_option[:num_chars]


def get_standings(standings_option='all', date_str=None):
    if date_str is None:
        date_str = time.strftime("%Y-%m-%d")
    LOG.debug('Getting standings for %s, option=%s', date_str, standings_option)
    if _match(standings_option, 'all') or _match(standings_option, 'division'):
        display_standings('byDivision', 'Division', date_str)
        _match(standings_option, 'all') and print('')
    if _match(standings_option, 'all') or _match(standings_option, 'conference'):
        display_standings('byConference', 'Conference', date_str, rank_tag='conferenceRank')
        _match(standings_option, 'all') and print('')
    if _match(standings_option, 'all') or _match(standings_option, 'wildcard'):
        display_standings('wildCard', 'Wildcard', date_str, rank_tag='wildCardRank')
        _match(standings_option, 'all') and print('')
    if _match(standings_option, 'all') or _match(standings_option, 'overall') or _match(standings_option, 'league'):
        display_standings('byLeague', 'League', date_str, rank_tag='leagueRank')

    if _match(standings_option, 'playoff') or _match(standings_option, 'postseason'):
        display_standings('postseason', 'Playoffs', date_str)
    if _match(standings_option, 'preseason'):
        display_standings('preseason', 'Preseason', date_str)


def display_standings(standings_type, display_title, date_str, rank_tag='divisionRank', header_tags=('conference', 'division')):
    url = STANDINGS_URL.format(standings_type=standings_type, date=date_str)
    json_data = util.request_json(url, 'standings')

    border = displayutil.Border(use_unicode=config.UNICODE)

    outl = list()
    if display_title != '':
        outl.append('{color_on}{name:22}\t{win:^2} {ot:^2} {loss:^2} {point:^3} {streak}{color_off}'
                    .format(color_on=border.border_color,
                            name='   {thickborder} {title} {thickborder}'.format(title=display_title,
                                                                                 thickborder=border.doubledash * int((29-len(display_title))/2 - 1)),
                            win='W', ot='OT',
                            loss='L', point='P',
                            streak='Streak',
                            color_off=ANSI.reset()))

    needs_line_hr = False
    for record in json_data['records']:
        if standings_type == record['standingsType']:
            if needs_line_hr > 0:
                pass
                # outl.append('-' * 10)
            header = ''
            for tag in header_tags:
                if tag in record:
                    if 'name' in record[tag]:
                        header = _add_to_header(header, record[tag]['name'])
                    else:
                        header = _add_to_header(header, record[tag])
            if header:
                header = '{color_on}{b1} {title} {b2}{color_off}'.format(color_on=border.border_color,
                                                                         title=header,
                                                                         b1=border.dash*3,
                                                                         b2=border.dash*(41-len(header)),
                                                                         color_off=ANSI.reset())
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
                    color_on = ANSI.fg(config.CONFIG.parser['fav_colour'])
                    color_off = ANSI.reset()
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
