import configparser
import inspect
import logging
import os
import sys


DEFAULT_STREAM_START_OFFSET_SECS = 240

LOG = logging.getLogger(__name__)


DEFAULTS = {  # is applied to initial config before reading from file - these are the defaults:
    'nhlv': {
        'username': '',
        'password': '',
        'use_rogers': 'false',
        'favs': '',
        'fav_colour': 'blue',
        'scores': 'true',
        'use_short_feeds': 'true',
        'filter': '',
        'cdn': 'akamai',
        'resolution': '720p_alt',
        'video_player': 'mpv',

        'api_url': 'http://statsapi.web.nhl.com/api/v1/',
        # 'mf_svc_url': 'https://mf.svc.nhl.com/ws/media/mf/v2.4/stream',
        'mf_svc_url': 'https://mf.svc.nhl.com/ws/media/mf/v2.4/stream?contentId={}&playbackScenario={}&platform={}&sessionKey={}&cdnName={}',
        'ua_nhl': 'NHL/11479 CFNetwork/887 Darwin/17.0.0',
        'svc_user_agent': 'NHL/11479 CFNetwork/887 Darwin/17.0.0',

        'streamlink_highlights': 'true',  # if false will send url direct to video_player (no resolution selection)
        'streamlink_passthrough_highlights': 'true',  # allows seeking
        'streamlink_passthrough': 'false',
        'streamlink_hls_audio_select': '*',
        'streamlink_extra_args': '',
        'stream_start_offset_secs': str(DEFAULT_STREAM_START_OFFSET_SECS),
        'audio_player': 'mpv',
        'debug': 'false',
        'verbose': 'false',
        'game_critical_colour': 'yellow',
        'verify_ssl': 'true',
        'save_json_file_by_timestamp': 'false',
        'unicode': 'true',
    }
}
