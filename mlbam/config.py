import configparser
import inspect
import logging
import os
import sys


HIGHLIGHT_FEEDTYPES = ('condensed', 'recap')

# Note: 720p (best) is the 60fps stream
BANDWIDTH_CHOICES = ('worst', '360p', '540p', '720p_alt', '720p', 'best')

CONFIG = None  # holds a Config instance

# These are initialized/updated via the Config class
DEBUG = False
VERBOSE = False
VERIFY_SSL = True
SAVE_JSON_FILE = True
SAVE_JSON_FILE_BY_TIMESTAMP = False  # normally false; will save many .json files if set
SAVE_PLAYLIST_FILE = False
UNICODE = True

LOG = logging.getLogger(__name__)


class Config:
    """Contains the configuration data for use within the application, including a configparser instance
    for pulling in configuration from the 'config' file."""
    defaults = {  # is applied to initial config before reading from file - these are the defaults:
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
            'resolution': 'best',
            'video_player': 'mpv',
            'streamlink_highlights': 'true',  # if false will send url direct to video_player (no resolution selection)
            'streamlink_passthrough_highlights': 'true',  # allows seeking
            'streamlink_passthrough': 'false',
            'stream_start_offset_secs': '240',
            'audio_player': 'mpv',
            'debug': 'false',
            'verbose': 'false',
            'game_critical_colour': 'yellow',
            'verify_ssl': 'true',
            'save_json_file_by_timestamp': 'false',
            'unicode': 'true',
        }
    }
    config_dir_roots = ('.', os.path.join(os.environ['HOME'], '.config'), )
    platform = 'IPHONE'
    playback_scenario = 'HTTP_CLOUD_TABLET_60'
    ua_pc = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36'
    ua_iphone = 'AppleCoreMedia/1.0.0.15B202 (iPhone; U; CPU OS 11_1_2 like Mac OS X; en_us)'

    def __init__(self):
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.dir = self.__find_config_dir(script_name)
        self.parser = self.__init_configparser(script_name)
        global DEBUG
        DEBUG = self.parser.getboolean('debug', DEBUG)
        global VERBOSE
        VERBOSE = self.parser.getboolean('verbose', VERBOSE)
        global VERIFY_SSL
        VERIFY_SSL = self.parser.getboolean('verify_ssl', VERIFY_SSL)
        global UNICODE
        UNICODE = self.parser.getboolean('unicode', UNICODE)

    @staticmethod
    def __find_config_dir(script_name):
        # use the script name minus any extension for the config directory
        config_dir = None
        searched_paths = list()
        for config_dir_base in Config.config_dir_roots:
            for config_dir_name in (script_name, '.' + script_name):
                d = os.path.join(config_dir_base, config_dir_name)
                searched_paths.append(d)
                if os.path.exists(d) and os.path.isdir(d):
                    config_dir = d
                    break
            if config_dir is not None:
                break
        if config_dir is None:
            print('No config directory found, using current directory. [searched: {}]'.format(','.join(searched_paths)))
            config_dir = '.'
        return config_dir

    def __init_configparser(self, script_name):
        # now look for config file
        parser = configparser.ConfigParser()
        parser.read_dict(Config.defaults)
        ini_file = os.path.join(self.dir, 'config')
        if os.path.exists(ini_file):
            LOG.debug("Reading config file: {}".format(ini_file))
            with open(ini_file, 'r') as f:
                config_string = '[{}]\n'.format(script_name) + f.read()
                parser.read_string(config_string)
        return parser[script_name]

    @staticmethod
    def generate_config(username=None, password=None):
        """Creates config file from template + user prompts."""
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        # use the script name minus any extension for the config directory
        config_dir = None
        searched_paths = list()
        config_dir = os.path.join(Config.config_dir_roots[1], script_name)
        if not os.path.exists(config_dir):
            print("Creating config directory: {}".format(config_dir))
            os.makedirs(config_dir)
        config_file = os.path.join(config_dir, 'config')
        if os.path.exists(config_file):
            print("Aborting: The config file already exists at '{}'".format(config_file))
            return False

        # copy the template config file
        print("Generating basic config file at: {}".format(config_dir))
        current_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
        template_config_path = os.path.abspath(os.path.join(current_dir, '..', 'config'))
        if not os.path.exists(template_config_path):
            print("Could not find template config file [expected at: {}]".format(template_config_path))
            return False

        if username is None:
            username = input('Enter MLB.tv username: ')
        if password is None:
            password = input('Enter MLB.tv password: ')

        with open(template_config_path, 'r') as infile, open(config_file, 'w') as outfile:
            for line in infile:
                if line.startswith('# username='):
                    outfile.write("username={}\n".format(username))
                elif line.startswith('# password='):
                    outfile.write("password={}\n".format(password))
                else:
                    outfile.write(line)
        print("Finished creating config file: {}".format(config_file))
        print("You may want to edit it now to set up favourites, etc.")



class NHLConfig(Config):
    """Configuration specific to NHL."""
    api_url = 'http://statsapi.web.nhl.com/api/v1/'
    mf_svc_url = 'https://mf.svc.nhl.com/ws/media/mf/v2.4/stream'
    ua_nhl = 'NHL/11479 CFNetwork/887 Darwin/17.0.0'
    svc_user_agent = 'NHL/11479 CFNetwork/887 Darwin/17.0.0'

    def __init__(self):
        Config.__init__(self)

