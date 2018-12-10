"""
Streaming functions
"""

import logging
import os
import requests
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

from datetime import datetime
from datetime import timezone
from dateutil import tz
from dateutil import parser

import mlbam.auth as auth
import mlbam.common.util as util
import mlbam.common.config as config
import mlbam.common.stream as stream


LOG = logging.getLogger(__name__)


def select_feed_for_team(game_rec, team_code, feedtype=None):
    found = False
    if game_rec['away']['abbrev'] == team_code:
        found = True
        if feedtype is None and 'away' in game_rec['feed']:
            feedtype = 'away'  # assume user wants their team's feed
    elif game_rec['home']['abbrev'] == team_code:
        found = True
        if feedtype is None and 'home' in game_rec['feed']:
            feedtype = 'home'  # assume user wants their team's feed
    if found:
        if feedtype is None:
            LOG.info('Default (home/away) feed not found: choosing first available feed')
            if len(game_rec['feed']) > 0:
                feedtype = list(game_rec['feed'].keys())[0]
                LOG.info("Chose '{}' feed (override with --feed option)".format(feedtype))
        if feedtype not in game_rec['feed']:
            LOG.error("Feed is not available: {}".format(feedtype))
            return None, None
        return game_rec['feed'][feedtype]['mediaPlaybackId'], game_rec['feed'][feedtype]['eventId']
    return None, None


def find_highlight_url_for_team(game_rec, feedtype):
    if feedtype not in config.HIGHLIGHT_FEEDTYPES:
        raise Exception('highlight: feedtype must be condensed or recap')
    if feedtype in game_rec['feed'] and 'playback_url' in game_rec['feed'][feedtype]:
        return game_rec['feed'][feedtype]['playback_url']
    LOG.error('No playback_url found for {} vs {}'.format(game_rec['away']['abbrev'], game_rec['home']['abbrev']))
    return None


def fetch_stream(game_pk, content_id, event_id):
    """ game_pk: game_pk
        event_id: eventId
        content_id: mediaPlaybackId
    """
    stream_url = None
    media_auth = None

    auth_cookie = auth.get_auth_cookie()
    if auth_cookie is None:
        LOG.error("fetch_stream: not logged in")
        return stream_url, media_auth

    session_key = auth.get_session_key(game_pk, event_id, content_id, auth_cookie)
    if session_key is None:
        return stream_url, media_auth
    elif session_key == 'blackout':
        msg = ('The game you are trying to access is not currently available due to local '
               'or national blackout restrictions.\n'
               ' Full game archives will be available 48 hours after completion of this game.')
        LOG.info('Game Blacked Out: {}'.format(msg))
        return stream_url, media_auth

    # Get user set CDN
    if config.CONFIG.parser['cdn'] == 'akamai':
        cdn = 'MED2_AKAMAI_SECURE'
    elif config.CONFIG.parser['cdn'] == 'level3':
        cdn = 'MED2_LEVEL3_SECURE'

    url = config.CONFIG.parser['mf_svc_url'].format(content_id, config.CONFIG.playback_scenario,
                                                    config.CONFIG.platform, urllib.parse.quote_plus(session_key), cdn)

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
        "Authorization": auth_cookie,
        "User-Agent": config.CONFIG.parser['svc_user_agent'],
        "Proxy-Connection": "keep-alive"
    }

    util.log_http(url, 'get', headers, sys._getframe().f_code.co_name)
    # json_source = requests.get(url, headers=headers, cookies=auth.load_cookies(), verify=config.VERIFY_SSL).json()
    response = requests.get(url, headers=headers, cookies=auth.load_cookies(), verify=config.VERIFY_SSL)
    json_source = response.json()
 
    #if json_source is not None and config.SAVE_JSON_FILE:
    if json_source is not None:
        output_filename = 'stream'
        if 1:  # config.SAVE_JSON_FILE_BY_TIMESTAMP:
            json_file = os.path.join(util.get_tempdir(),
                                     '{}-{}.json'.format(output_filename, time.strftime("%Y-%m-%d-%H%M")))
        else:
            json_file = os.path.join(util.get_tempdir(), '{}.json'.format(output_filename))
        with open(json_file, 'w') as out:  # write date to json_file
            out.write(response.text)

    if json_source['status_code'] == 1:
        media_item = json_source['user_verified_event'][0]['user_verified_content'][0]['user_verified_media_item'][0]
        if media_item['blackout_status']['status'] == 'BlackedOutStatus':
            msg = ('The game you are trying to access is not currently available due to local '
                   'or national blackout restrictions.\n'
                   'Full game archives will be available 48 hours after completion of this game.')
            util.die('Game Blacked Out: {}'.format(msg))
        elif media_item['auth_status'] == 'NotAuthorizedStatus':
            msg = 'You do not have an active subscription. To access this content please purchase a subscription.'
            util.die('Account Not Authorized: {}'.format(msg))
        else:
            stream_url = media_item['url']
            media_auth = '{}={}'.format(str(json_source['session_info']['sessionAttributes'][0]['attributeName']),
                                        str(json_source['session_info']['sessionAttributes'][0]['attributeValue']))
            if session_key in json_source:
                session_key = json_source['session_key']
                auth.update_session_key(session_key)
    else:
        msg = json_source['status_message']
        util.die('Error Fetching Stream: {}', msg)

    LOG.debug('fetch_stream stream_url: %s', stream_url)
    LOG.debug('fetch_stream media_auth: %s', media_auth)
    return stream_url, media_auth


def save_playlist_to_file(stream_url, media_auth):
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
        "User-Agent": config.CONFIG.parser['svc_user_agent'],
        "Cookie": media_auth
    }
    util.log_http(stream_url, 'get', headers, sys._getframe().f_code.co_name)
    playlist = requests.get(stream_url, headers=headers, cookies=auth.load_cookies(), verify=config.VERIFY_SSL).text
    playlist_file = os.path.join(config.CONFIG.dir, 'playlist-{}.m3u8'.format(time.strftime("%Y-%m-%d")))
    LOG.debug('writing playlist to: %s', playlist_file)
    with open(playlist_file, 'w') as handle:
        handle.write(playlist)
    LOG.debug('save_playlist_to_file: %s', playlist)


def get_game_rec(game_data, team_to_play):
    """
    """
    game_rec = None
    for game_pk in game_data:
        if team_to_play in (game_data[game_pk]['away']['abbrev'], game_data[game_pk]['home']['abbrev']):
            game_rec = game_data[game_pk]
            break
    if game_rec is None:
        util.die("No game found for team {}".format(team_to_play))
    return game_rec


def play_stream(game_rec, team_to_play, feedtype, date_str, fetch, login_func, from_start, offset=None, duration=None, is_multi_highlight=False):
    if feedtype is not None and feedtype in config.HIGHLIGHT_FEEDTYPES:
        # handle condensed/recap
        playback_url = find_highlight_url_for_team(game_rec, feedtype)
        if playback_url is None:
            util.die("No playback url for feed '{}'".format(feedtype))
        stream.play_highlight(playback_url,
                              stream.get_fetch_filename(date_str, game_rec['home']['abbrev'],
                                                        game_rec['away']['abbrev'], feedtype, fetch),
                              is_multi_highlight)
    else:
        # handle full game (live or archive)
        # this is the only feature requiring an authenticated session
        auth_cookie = auth.get_auth_cookie()
        if auth_cookie is None:
            login_func()
            # auth.login(config.CONFIG.parser['username'],
            #            config.CONFIG.parser['password'],
            #            config.CONFIG.parser.getboolean('use_rogers', False))
        LOG.debug('Authorization cookie: %s', auth.get_auth_cookie())

        media_playback_id, event_id = select_feed_for_team(game_rec, team_to_play, feedtype)
        if media_playback_id is not None:
            stream_url, media_auth = fetch_stream(game_rec['game_pk'], media_playback_id, event_id)
            if stream_url is not None:
                if config.SAVE_PLAYLIST_FILE:
                    save_playlist_to_file(stream_url, media_auth)
                streamlink(stream_url, media_auth,
                           stream.get_fetch_filename(date_str, game_rec['home']['abbrev'],
                                                     game_rec['away']['abbrev'], feedtype, fetch),
                           from_start, offset, duration)
            else:
                LOG.error("No stream URL found")
        else:
            LOG.info("No game stream found for %s", team_to_play)
    return 0


def streamlink(stream_url, media_auth, fetch_filename=None, from_start=False, offset=None, duration=None):
    LOG.debug("Stream url: %s", stream_url)
    auth_cookie_str = "Authorization=" + auth.get_auth_cookie()
    media_auth_cookie_str = media_auth
    user_agent_hdr = 'User-Agent=' + config.CONFIG.ua_iphone

    video_player = config.CONFIG.parser['video_player']
    streamlink_cmd = ["streamlink",
                      "--http-no-ssl-verify",
                      "--player-no-close",
                      "--http-cookie", auth_cookie_str,
                      "--http-cookie", media_auth_cookie_str,
                      "--http-header", user_agent_hdr,
                      "--hls-timeout", "600",         # default: 60
                      "--hls-segment-timeout", "60"]  # default: 10
    if from_start:
        streamlink_cmd.append("--hls-live-restart")
        LOG.info("Starting from beginning [--hls-live-restart]")
    elif offset:
        streamlink_cmd.append("--hls-start-offset")
        streamlink_cmd.append(offset)
        LOG.info("Using --hls-start-offset %s", offset)

    if duration:
        streamlink_cmd.append("--hls-duration")
        streamlink_cmd.append(duration)
        LOG.info("Using --hls-duration %s", duration)

    if fetch_filename is not None:
        if os.path.exists(fetch_filename):
            # don't overwrite existing file - use a new name based on hour,minute
            fetch_filename_orig = fetch_filename
            fsplit = os.path.splitext(fetch_filename)
            fetch_filename = '{}-{}{}'.format(fsplit[0], datetime.strftime(datetime.today(), "%H%M"), fsplit[1])
            LOG.info('File %s exists, using %s instead', fetch_filename_orig, fetch_filename)
        streamlink_cmd.append("--output")
        streamlink_cmd.append(fetch_filename)
    elif video_player is not None and video_player != '':
        LOG.debug('Using video_player: %s', video_player)
        streamlink_cmd.append("--player")
        streamlink_cmd.append(video_player)
        if config.CONFIG.parser.getboolean('streamlink_passthrough', False):
            streamlink_cmd.append("--player-passthrough=hls")
    if config.VERBOSE:
        streamlink_cmd.append("--loglevel")
        streamlink_cmd.append("debug")
    streamlink_cmd.append(stream_url)
    streamlink_cmd.append(config.CONFIG.parser.get('resolution', 'best'))

    LOG.debug('Playing: %s', str(streamlink_cmd))
    subprocess.run(streamlink_cmd)

    return streamlink_cmd
