"""
"""
import datetime
import io
import logging
import os
import re
import time
import sys

import lxml
import lxml.etree

import mlbam.common.config as config
import mlbam.common.util as util
import mlbam.common.session as session


LOG = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0.4"
PLATFORM = "macintosh"

# BAM_SDK_VERSION = "3.0"
# 
# API_KEY_URL = "https://www.mlb.com/tv/g490865/"
# API_KEY_RE = re.compile(r'"apiKey":"([^"]+)"')
# CLIENT_API_KEY_RE = re.compile(r'"clientApiKey":"([^"]+)"')
# 
# TOKEN_URL_TEMPLATE = "https://media-entitlement.mlb.com/jwt?ipid={ipid}&fingerprint={fingerprint}==&os={platform}&appname=mlbtv_web"
# 
# GAME_CONTENT_URL_TEMPLATE = "http://statsapi.mlb.com/api/v1/game/{game_id}/content"
# 
# # GAME_FEED_URL = "http://statsapi.mlb.com/api/v1/game/{game_id}/feed/live"
# 
# SCHEDULE_TEMPLATE = (
#     "http://statsapi.mlb.com/api/v1/schedule?sportId={sport_id}&startDate={start}&endDate={end}"
#     "&gameType={game_type}&gamePk={game_id}&teamId={team_id}"
#     "&hydrate=linescore,team,game(content(summary,media(epg)),tickets)"
# )
# 
# ACCESS_TOKEN_URL = "https://edge.bamgrid.com/token"
# 
# STREAM_URL_TEMPLATE = "https://edge.svcs.mlb.com/media/{media_id}/scenarios/browser"



class NHLSession(session.Session):

    def __init__(self):
        session.Session.__init__(self, USER_AGENT, PLATFORM)

    def login(self):
        """Authenticates user to nhl site."""
        if self.is_logged_in():
            LOG.debug("already logged in")
            return

        url = 'https://user.svc.nhl.com/oauth/token?grant_type=client_credentials'
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Accept-Language": "en-US,en;q=0.8",
            "User-Agent": config.CONFIG.ua_pc,
            "Origin": "https://www.nhl.com",
            "Authorization": "Basic d2ViX25obC12MS4wLjA6MmQxZDg0NmVhM2IxOTRhMThlZjQwYWM5ZmJjZTk3ZTM=",
        }
        userid = config.CONFIG.parser['username']
        passwd = config.CONFIG.parser['password']
        use_rogers = config.CONFIG.parser.getboolean('use_rogers', False)
        util.log_http(url, 'post', headers, sys._getframe().f_code.co_name)
        resp = self.session.post(url, headers=headers, data='', verify=config.VERIFY_SSL)
        # r = requests.post(url, headers=headers, data='', cookies=load_cookies(), verify=config.VERIFY_SSL)
        if resp.status_code >= 400:
            util.die("Authorization cookie couldn't be downloaded.")
        json_source = resp.json()

        auth_cookie = json_source['access_token']

        if use_rogers:
            LOG.info("Logging in via Rogers")
            url = 'https://activation-rogers.svc.nhl.com/ws/subscription/flow/rogers.login'
            login_data = '{"rogerCredentials":{"email":%s,"password":%s}}' % (userid, passwd)
            # referer = "https://www.nhl.com/login/rogers"
        else:
            LOG.info("Logging in via NHL")
            url = 'https://user.svc.nhl.com/v2/user/identity'
            login_data = '{"email":{"address":%s},"type":"email-password","password":{"value":%s}}' % (userid, passwd)

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Accept-Language": "en-US,en;q=0.8",
            "Content-Type": "application/json",
            "Authorization": auth_cookie,
            "Connection": "keep-alive",
            "User-Agent": config.CONFIG.ua_pc
        }

        util.log_http(url, 'post', headers, sys._getframe().f_code.co_name)
        r = requests.post(url, headers=headers, data=login_data, cookies=load_cookies(), verify=config.VERIFY_SSL)
        if r.status_code >= 400:
            try:
                json_source = r.json()
                msg = json_source['message']
            except Exception as e:
                msg = "Please check that your username and password are correct"
            LOG.debug('Login Error: json_source: %s', json_source)
            util.die('Login Error: {}'.format(msg))

        LOG.debug('Login successful')
        save_cookies(r.cookies)

        initial_url = "https://secure.mlb.com/enterworkflow.do?flowId=registration.wizard&c_id=mlb"
        # res = self.session.get(initial_url)
        # if not res.status_code == 200:
        #     raise SessionException(res.content)
        data = {
            "uri": "/account/login_register.jsp",
            "registrationAction": "identify",
            "emailAddress": config.CONFIG.parser['username'],
            "password": config.CONFIG.parser['password'],
            "submitButton": ""
        }
        LOG.info("Logging in")

        # resp =
        self.session.post("https://securea.mlb.com/authenticate.do",
                          data=data,
                          headers={"Referer": initial_url})

    def is_logged_in(self):
        # logged_in_url = "https://web-secure.mlb.com/enterworkflow.do?flowId=registration.newsletter&c_id=mlb"
        # content = self.session.get(logged_in_url).text
        # parser = lxml.etree.HTMLParser()
        # data = lxml.etree.parse(io.StringIO(content), parser)
        # if "Login/Register" in data.xpath(".//title")[0].text:
        #     return False
        # return True
        return False

    def get_access_token(self):
        url = 'https://user.svc.nhl.com/oauth/token?grant_type=client_credentials'
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Accept-Language": "en-US,en;q=0.8",
            "User-Agent": config.CONFIG.ua_pc,
            "Origin": "https://www.nhl.com",
            "Authorization": "Basic d2ViX25obC12MS4wLjA6MmQxZDg0NmVhM2IxOTRhMThlZjQwYWM5ZmJjZTk3ZTM=",
        }
        util.log_http(url, 'post', headers, sys._getframe().f_code.co_name)
        resp = self.session.post(url, headers=headers, data='', verify=config.VERIFY_SSL)
        # r = requests.post(url, headers=headers, data='', cookies=load_cookies(), verify=config.VERIFY_SSL)
        if resp.status_code >= 400:
            util.die("Authorization cookie couldn't be downloaded.")
        #response.raise_for_status()
        json_source = resp.json()
        auth_cookie = json_source['access_token']
        expiry = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=json_source["expires_in"])

        return auth_cookie, expiry

    def lookup_stream_url(self, game_pk, media_id):
        """ game_pk: game_pk
            media_id: mediaPlaybackId
        """
        stream_url = None
        headers = {
            "Authorization": self.access_token,
            "User-agent": USER_AGENT,
            "Accept": "application/vnd.media-service+json; version=1",
            "x-bamsdk-version": "3.0",
            "x-bamsdk-platform": PLATFORM,
            "origin": "https://www.mlb.com"
        }
        response = self.session.get(STREAM_URL_TEMPLATE.format(media_id=media_id), headers=headers)
        if response is not None and config.SAVE_JSON_FILE:
            output_filename = 'stream'
            if config.SAVE_JSON_FILE_BY_TIMESTAMP:
                json_file = os.path.join(util.get_tempdir(),
                                         '{}-{}.json'.format(output_filename, time.strftime("%Y-%m-%d-%H%M")))
            else:
                json_file = os.path.join(util.get_tempdir(), '{}.json'.format(output_filename))
            with open(json_file, 'w') as out:  # write date to json_file
                out.write(response.text)

        stream = response.json()
        LOG.debug("lookup_stream_url, stream response: %s", stream)
        if "errors" in stream and stream["errors"]:
            LOG.error("Could not load stream\n%s", stream)
            return None
        stream_url = stream['stream']['complete']
        return stream_url
