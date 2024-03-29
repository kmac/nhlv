"""
Session management

TODO: this module needs test cases around authentication
"""
# pylint: disable=len-as-condition, line-too-long

import datetime
import io
import logging
import os
import re
import requests
import time
import sys

import lxml
import lxml.etree

import mlbam.auth as auth
import mlbam.common.config as config
import mlbam.common.util as util
import mlbam.common.session as session


LOG = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0.4"
PLATFORM = "macintosh"

ACCESS_TOKEN_URL = 'https://user.svc.nhl.com/oauth/token?grant_type=client_credentials'
AUTH_STR = 'Basic d2ViX25obC12MS4wLjA6MmQxZDg0NmVhM2IxOTRhMThlZjQwYWM5ZmJjZTk3ZTM='
UA_PC = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36'


#
#  NOT USED - THIS CLASS IS NOT USED
#
#
class NHLSession(session.Session):

    def __init__(self):
        session.Session.__init__(self, USER_AGENT, PLATFORM)

    def get_access_token(self):
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Accept-Language": "en-US,en;q=0.8",
            "User-Agent": config.CONFIG.ua_pc,
            "Origin": "https://www.nhl.com",
            "Authorization": AUTH_STR
        }
        util.log_http(ACCESS_TOKEN_URL, 'post', headers,
                      sys._getframe().f_code.co_name)
        resp = self.session.post(ACCESS_TOKEN_URL,
                                 headers=headers,
                                 data='',
                                 verify=config.VERIFY_SSL)
        # r = requests.post(url, headers=headers, data='', \
        #        cookies=load_cookies(), verify=config.VERIFY_SSL)
        if resp.status_code >= 400:
            util.die("Authorization cookie couldn't be downloaded.")
        # response.raise_for_status()
        json_source = resp.json()
        auth_cookie = json_source['access_token']
        expiry = datetime.datetime.now(tz=datetime.timezone.utc) \
            + datetime.timedelta(seconds=json_source["expires_in"])

        return auth_cookie, expiry

    def login(self):
        """Authenticates user to nhl site."""
        # pylint: disable=too-many-locals
        if self.is_logged_in():
            LOG.debug("already logged in")
            return

        login_url = None
        userid = config.CONFIG.parser['username']
        passwd = config.CONFIG.parser['password']
        use_rogers = config.CONFIG.parser.getboolean('use_rogers', False)
        if use_rogers:
            LOG.info("Logging in via Rogers")
            login_url = 'https://activation-rogers.svc.nhl.com/ws/subscription/flow/rogers.login'
            #login_data = '{"rogerCredentials":{"email":%s,"password":%s}}' % (userid, passwd)
            login_data = {"rogerCredentials": {"email": userid, "password": passwd}}
            # referer = "https://www.nhl.com/login/rogers"
        else:
            LOG.info("Logging in via NHL")
            login_url = 'https://user.svc.nhl.com/v2/user/identity'
            #login_data = '{"email":{"address":%s},"type":"email-password","password":{"value":%s}}' % (userid, passwd)
            login_data = {"email":{"address": userid},"type":"email-password","password":{"value": passwd}}

        auth_cookie, _ = self.get_access_token()
        # "Accept": "*/*",
        # "Accept-Encoding": "identity",
        # "Accept-Language": "en-US,en;q=0.8",
        # "Connection": "keep-alive",
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": auth_cookie,
            "User-Agent": UA_PC
        }

        util.log_http(login_url, 'post', headers,
                      sys._getframe().f_code.co_name)
        resp = requests.post(login_url,
                             headers=headers,
                             json=login_data,
                             cookies=auth_cookie,
                             verify=config.VERIFY_SSL)
        if resp.status_code >= 400:
            try:
                json_source = resp.json()
                msg = json_source['message']
            except Exception as e:
                msg = "Please check that your username and password are correct"
            LOG.debug('Login Error: json_source: %s', json_source)
            util.die('Login Error: {}'.format(msg))

        LOG.debug('Login successful')
        auth.save_cookies(resp.cookies)

        # initial_url = ('https://secure.mlb.com/enterworkflow.do?'
        #                'flowId=registration.wizard&c_id=mlb')
        # # res = self.session.get(initial_url)
        # # if not res.status_code == 200:
        # #     raise SessionException(res.content)
        # data = {
        #     "uri": "/account/login_register.jsp",
        #     "registrationAction": "identify",
        #     "emailAddress": config.CONFIG.parser['username'],
        #     "password": config.CONFIG.parser['password'],
        #     "submitButton": ""
        # }
        # LOG.info("Logging in")

        # # resp =
        # self.session.post("https://securea.mlb.com/authenticate.do",
        #                   data=data,
        #                   headers={"Referer": initial_url})

    def is_logged_in(self):
        # logged_in_url = "https://web-secure.mlb.com/enterworkflow.do?flowId=registration.newsletter&c_id=mlb"
        # content = self.session.get(logged_in_url).text
        # parser = lxml.etree.HTMLParser()
        # data = lxml.etree.parse(io.StringIO(content), parser)
        # if "Login/Register" in data.xpath(".//title")[0].text:
        #     return False
        # return True
        return False

    # def lookup_stream_url(self, game_pk, media_id):
    #     """ game_pk: game_pk
    #         media_id: mediaPlaybackId
    #     """
    #     stream_url = None
    #     headers = {
    #         "Authorization": self.access_token,
    #         "User-agent": USER_AGENT,
    #         "Accept": "application/vnd.media-service+json; version=1",
    #         "x-bamsdk-version": "3.0",
    #         "x-bamsdk-platform": PLATFORM,
    #         "origin": "https://www.mlb.com"
    #     }
    #     response = self.session.get(
    #         STREAM_URL_TEMPLATE.format(media_id=media_id), headers=headers)
    #     if response is not None and config.SAVE_JSON_FILE:
    #         output_filename = 'stream'
    #         if config.SAVE_JSON_FILE_BY_TIMESTAMP:
    #             json_file = os.path.join(
    #                 util.get_tempdir(),
    #                 '{}-{}.json'.format(output_filename,
    #                                     time.strftime("%Y-%m-%d-%H%M")))
    #         else:
    #             json_file = os.path.join(util.get_tempdir(),
    #                                      '{}.json'.format(output_filename))
    #         with open(json_file, 'w') as out:  # write date to json_file
    #             out.write(response.text)

    #     stream = response.json()
    #     LOG.debug("lookup_stream_url, stream response: %s", stream)
    #     if "errors" in stream and stream["errors"]:
    #         LOG.error("Could not load stream\n%s", stream)
    #         return None
    #     stream_url = stream['stream']['complete']
    #     return stream_url
