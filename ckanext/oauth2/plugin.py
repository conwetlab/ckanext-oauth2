# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of OAuth2 CKAN Extension.

# OAuth2 CKAN Extension is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OAuth2 CKAN Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with OAuth2 CKAN Extension.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import constants
import logging
import oauth2

from functools import partial
from ckan import plugins
from ckan.plugins import toolkit
from pylons import config
from urlparse import urlparse

log = logging.getLogger(__name__)


def _no_permissions(context, msg):
    user = context['user']
    return {'success': False, 'msg': msg.format(user=user)}


@toolkit.auth_sysadmins_check
def user_create(context, data_dict):
    msg = toolkit._('Users cannot be created.')
    return _no_permissions(context, msg)


@toolkit.auth_sysadmins_check
def user_update(context, data_dict):
    msg = toolkit._('Users cannot be edited.')
    return _no_permissions(context, msg)


@toolkit.auth_sysadmins_check
def user_reset(context, data_dict):
    msg = toolkit._('Users cannot reset passwords.')
    return _no_permissions(context, msg)


@toolkit.auth_sysadmins_check
def request_reset(context, data_dict):
    msg = toolkit._('Users cannot reset passwords.')
    return _no_permissions(context, msg)


class OAuth2Plugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IAuthenticator, inherit=True)
    plugins.implements(plugins.IAuthFunctions, inherit=True)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IConfigurer)

    def __init__(self, name=None):
        '''Store the OAuth 2 client configuration'''
        log.debug('Init OAuth2 extension')

        self.register_url = config.get('ckan.oauth2.register_url', None)
        self.reset_url = config.get('ckan.oauth2.reset_url', None)
        self.edit_url = config.get('ckan.oauth2.edit_url', None)
        self.authorization_header = config.get('ckan.oauth2.authorization_header', 'Authorization')

        self.oauth2helper = oauth2.OAuth2Helper()

    def before_map(self, m):
        log.debug('Setting up the redirections to the OAuth2 service')

        # We need to handle petitions received to the Callback URL
        # since some error can arise and we need to process them
        m.connect('/oauth2/callback',
                  controller='ckanext.oauth2.controller:OAuth2Controller',
                  action='callback')

        # # Redirect the user to the OAuth service register page
        if self.register_url:
            m.redirect('/user/register', self.register_url)

        # Redirect the user to the OAuth service reset page
        if self.reset_url:
            m.redirect('/user/reset', self.reset_url)

        # Redirect the user to the OAuth service reset page
        if self.edit_url:
            m.redirect('/user/edit/{user}', self.edit_url)

        return m

    def identify(self):
        log.debug('identify')

        def _refresh_and_save_token(user_name):
            new_token = self.oauth2helper.refresh_token(user_name)
            if new_token:
                toolkit.c.usertoken = new_token

        environ = toolkit.request.environ
        apikey = toolkit.request.headers.get(self.authorization_header, '')
        user_name = None

        # This API Key is not the one of CKAN, it's the one provided by the OAuth2 Service
        if apikey:
            try:
                token = {'access_token': apikey}
                user_name = self.oauth2helper.identify(token)
            except Exception:
                pass

        # If the authentication via API fails, we can still log in the user using session.
        if user_name is None and 'repoze.who.identity' in environ:
            user_name = environ['repoze.who.identity']['repoze.who.userid']
            log.info('User %s logged using session' % user_name)

        # If we have been able to log in the user (via API or Session)
        if user_name:
            toolkit.c.user = user_name
            toolkit.c.usertoken = self.oauth2helper.get_stored_token(user_name)
            toolkit.c.usertoken_refresh = partial(_refresh_and_save_token, user_name)
        else:
            log.warn('The user is not currently logged...')

    def _get_previous_page(self, default_page):
        if 'came_from' not in toolkit.request.params:
            came_from_url = toolkit.request.headers.get('Referer', default_page)
        else:
            came_from_url = toolkit.request.params.get('came_from', default_page)

        came_from_url_parsed = urlparse(came_from_url)

        # Avoid redirecting users to external hosts
        if came_from_url_parsed.netloc != '' and came_from_url_parsed.netloc != toolkit.request.host:
            came_from_url = default_page

        # When a user is being logged and REFERER == HOME or LOGOUT_PAGE
        # he/she must be redirected to the dashboard
        pages = ['/', '/user/logged_out_redirect']
        if came_from_url_parsed.path in pages:
            came_from_url = default_page

        return came_from_url

    def login(self):
        log.debug('login')

        # Log in attemps are fired when the user is not logged in and they click
        # on the log in button

        # Get the page where the user was when the loggin attemp was fired
        # When the user is not logged in, he/she should be redirected to the dashboard when
        # the system cannot get the previous page
        came_from_url = self._get_previous_page(constants.INITIAL_PAGE)

        self.oauth2helper.challenge(came_from_url)

    def abort(self, status_code, detail, headers, comment):
        log.debug('abort')

        # If the user is authenticated, but they cannot access a protected resource, the system
        # should redirect them to the previous page. If the user is not redirected, the system
        # will try to reauthenticate the user generating a redirect loop:
        # (authenticate -> user not allowed -> auto log out -> authenticate -> ...)
        # If the user is not authenticated, the system should start the authentication process

        if toolkit.c.user:  # USER IS AUTHENTICATED
            # When the user is logged in, he/she should be redirected to the main page when
            # the system cannot get the previous page
            came_from_url = self._get_previous_page('/')

            # Init headers and set Location
            if headers is None:
                headers = {}
            headers['Location'] = came_from_url

            # 302 -> Found
            return 302, detail, headers, comment
        else:                # USER IS NOT AUTHENTICATED
            # By not modifying the received parameters, the authentication process will start
            return status_code, detail, headers, comment

    def get_auth_functions(self):
        # we need to prevent some actions being authorized.
        return {
            'user_create': user_create,
            'user_update': user_update,
            'user_reset': user_reset,
            'request_reset': request_reset
        }

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        plugins.toolkit.add_template_directory(config, 'templates')
