"""
Manages authentication with nhl.tv
"""
# pylint: disable=len-as-condition, line-too-long, missing-docstring

import http.cookiejar
import logging
import os
import sys
import time

from datetime import datetime
from datetime import timedelta

import requests

import mlbam.common.util as util
import mlbam.common.config as config


LOG = logging.getLogger(__name__)

AUTH_STR = 'Basic d2ViX25obC12MS4wLjA6MmQxZDg0NmVhM2IxOTRhMThlZjQwYWM5ZmJjZTk3ZTM='
ACCESS_TOKEN_URL = 'https://user.svc.nhl.com/oauth/token?grant_type=client_credentials'
ROGERS_LOGIN_URL = 'https://activation-rogers.svc.nhl.com/ws/subscription/flow/rogers.login'
NHL_LOGIN_URL = 'https://user.svc.nhl.com/v2/user/identity'


def get_cookie_file():
    return os.path.join(config.CONFIG.dir, 'cookies.lwp')


def load_cookies():
    """Load cookies from file."""
    cookie_file = get_cookie_file()
    cookie_jar = http.cookiejar.LWPCookieJar()
    if os.path.exists(cookie_file):
        LOG.debug('Loading cookies from %s', cookie_file)
        cookie_jar.load(cookie_file, ignore_discard=True)
    return cookie_jar


def save_cookies(cookiejar):
    """Save cookies to file."""
    LOG.debug('Saving cookies')
    cookie_file = get_cookie_file()
    cookie_jar = http.cookiejar.LWPCookieJar()
    if os.path.exists(cookie_file):
        cookie_jar.load(cookie_file, ignore_discard=True)
    for cookie in cookiejar:
        args = dict(list(vars(cookie).items()))
        args['rest'] = args['_rest']
        del args['_rest']
        cookie = http.cookiejar.Cookie(**args)
        cookie_jar.set_cookie(cookie)
    cookie_jar.save(cookie_file, ignore_discard=True)


def get_auth_cookie():
    """Get authentication cookie from file."""
    auth_cookie = None
    cookie_jar = load_cookies()
    for cookie in cookie_jar:
        if cookie.name == "Authorization" and not cookie.is_expired():
            auth_cookie = cookie.value
    return auth_cookie


def nhl_login():
    """Authenticates user to nhl site."""
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
    resp = requests.post(ACCESS_TOKEN_URL,
                         headers=headers,
                         data='',
                         cookies=load_cookies(),
                         verify=config.VERIFY_SSL)
    if resp.status_code >= 400:
        util.die("Authorization cookie couldn't be downloaded.")
    json_source = resp.json()

    if get_auth_cookie() is not None:
        LOG.debug('login: already logged in (we have a valid cookie)')
        return

    auth_cookie = json_source['access_token']

    userid = config.CONFIG.parser['username']
    passwd = config.CONFIG.parser['password']
    use_rogers = config.CONFIG.parser.getboolean('use_rogers', False)
    if use_rogers:
        LOG.info("Logging in via Rogers")
        login_url = ROGERS_LOGIN_URL
        login_data = {
            "rogerCredentials": {
                "email": userid,
                "password": passwd
            }
        }
    else:
        LOG.info("Logging in via NHL")
        login_url = NHL_LOGIN_URL
        login_data = {
            "email": {
                "address": userid
            },
            "type": "email-password",
            "password": {
                "value": passwd
            }
        }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": auth_cookie,
        "User-Agent": config.CONFIG.ua_pc
    }

    util.log_http(login_url, 'post', headers, sys._getframe().f_code.co_name)
    resp = requests.post(login_url,
                         headers=headers,
                         json=login_data,
                         cookies=load_cookies(),
                         verify=config.VERIFY_SSL)
    if resp.status_code >= 400:
        try:
            json_source = resp.json()
            msg = json_source['message']
        except Exception as e:
            msg = ('Please check that your username and password are correct'
                   ' [%s]') % e
        LOG.debug('Login Error: %s, json_source: %s', msg, json_source)
        util.die('Login Error: {}'.format(msg))

    LOG.debug('Login successful')
    save_cookies(resp.cookies)


def update_session_key(session_key):
    """ save session_key to file """
    session_key_file = os.path.join(config.CONFIG.dir, 'sessionkey')
    with open(session_key_file, 'w') as handle:
        print(session_key, file=handle)


def get_session_key(game_pk, event_id, content_id, auth_cookie):
    """ game_pk: game_pk
        event_id: eventId
        content_id: mediaPlaybackId
    """
    session_key_file = os.path.join(config.CONFIG.dir, 'sessionkey')
    if os.path.exists(session_key_file):
        if datetime.today() - datetime.fromtimestamp(os.path.getmtime(session_key_file)) < timedelta(days=1):
            with open(session_key_file, 'r') as handle:
                for line in handle:
                    session_key = line.strip()
                    LOG.debug('Using cached session key: %s', session_key)
                    return session_key
    LOG.debug("Requesting session key")
    epoch_time_now = str(int(round(time.time()*1000)))
    url = 'https://mf.svc.nhl.com/ws/media/mf/v2.4/stream?eventId={}&format=json&platform={}&subject=NHLTV&_={}'
    url = url.format(event_id, config.CONFIG.platform, epoch_time_now)
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
        "Authorization": auth_cookie,
        "User-Agent": config.CONFIG.ua_pc,
        "Origin": "https://www.nhl.com",
        "Referer": "https://www.nhl.com/tv/{}/{}/{}".format(game_pk, event_id, content_id)
    }
    util.log_http(url, 'get', headers, sys._getframe().f_code.co_name)
    json_source = requests.get(url, headers=headers, cookies=load_cookies(), verify=config.VERIFY_SSL).json()
    LOG.debug('Session key json: %s', json_source)

    if json_source['status_code'] == 1:
        if json_source['user_verified_event'][0]['user_verified_content'][0]['user_verified_media_item'][0]['blackout_status']['status'] \
                == 'BlackedOutStatus':
            session_key = 'blackout'
            LOG.debug('Event blacked out: %s',
                      json_source['user_verified_event'][0]['user_verified_content'][0]['user_verified_media_item'][0])
        else:
            session_key = str(json_source['session_key'])
    else:
        msg = json_source['status_message']
        util.die('Could not get session key: {}'.format(msg))

    LOG.debug('Retrieved session key: %s', session_key)
    update_session_key(session_key)
    return session_key
