# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2018 Future Internet Consulting and Development Solutions S.L.

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

import logging
import os
import urllib.parse
from functools import partial

import ckan.model as model
from ckan import plugins
from ckan.common import g
from ckan.plugins import toolkit
from flask_login import current_user, login_user, logout_user

from ckanext.oauth2 import db
from ckanext.oauth2.oauth2 import OAuth2Helper

log = logging.getLogger(__name__)


def _no_permissions(context, msg):
    user = context['user']
    return {'success': False, 'msg': msg.format(user=user)}


def user_create(context, data_dict):
    msg = toolkit._('Users cannot be created.')
    return _no_permissions(context, msg)


def user_update(context, data_dict):
    msg = toolkit._('Users cannot be edited.')
    return _no_permissions(context, msg)


def user_reset(context, data_dict):
    msg = toolkit._('Users cannot reset passwords.')
    return _no_permissions(context, msg)


def request_reset(context, data_dict):
    msg = toolkit._('Users cannot reset passwords.')
    return _no_permissions(context, msg)


def _get_previous_page(default_page):
    if 'came_from' not in toolkit.request.args:
        came_from_url = toolkit.request.headers.get('Referer', default_page)
    else:
        came_from_url = toolkit.request.args.get('came_from', default_page)

    came_from_url_parsed = urllib.parse.urlparse(came_from_url)

    # Enforce HTTPS if the request is secure
    if toolkit.request.scheme == 'https':
        came_from_url = urllib.parse.urlunparse(
            ('https',) + came_from_url_parsed[1:]
        )
        came_from_url_parsed = urllib.parse.urlparse(came_from_url)

    # Avoid redirecting users to external hosts
    if came_from_url_parsed.netloc != '' and came_from_url_parsed.netloc != toolkit.request.host:
        came_from_url = default_page

    # When a user is being logged in and REFERER == HOME or LOGOUT_PAGE,
    # redirect to the default page instead
    pages = ['/', '/user/logged_out_redirect']
    if came_from_url_parsed.path in pages:
        came_from_url = default_page

    return came_from_url


class OAuth2Plugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IAuthenticator, inherit=True)
    plugins.implements(plugins.IAuthFunctions, inherit=True)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IMiddleware, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    _request_loader_installed = False
    _request_loader_attempted = False

    def __init__(self, name=None):
        """Store the OAuth 2 client configuration"""
        log.debug('Init OAuth2 extension')
        self.oauth2helper = OAuth2Helper()

    def get_blueprint(self):
        from ckanext.oauth2.views import get_blueprints
        return get_blueprints()

    def get_auth_functions(self):
        return {
            'user_create': user_create,
            'user_update': user_update,
            'user_reset': user_reset,
            'request_reset': request_reset
        }

    def update_config(self, config):
        self.register_url = os.environ.get("CKAN_OAUTH2_REGISTER_URL", config.get('ckan.oauth2.register_url', None))
        self.reset_url = os.environ.get("CKAN_OAUTH2_RESET_URL", config.get('ckan.oauth2.reset_url', None))
        self.edit_url = os.environ.get("CKAN_OAUTH2_EDIT_URL", config.get('ckan.oauth2.edit_url', None))
        self.authorization_header = os.environ.get(
            "CKAN_OAUTH2_AUTHORIZATION_HEADER",
            config.get('ckan.oauth2.authorization_header', 'Authorization')
        ).lower()

        plugins.toolkit.add_template_directory(config, 'templates')

    def make_middleware(self, app, config):
        """Exempt CKAN API blueprint from CSRF so Bearer token API calls work.

        CKAN 2.11 enables Flask-WTF CSRFProtect globally but does not exempt
        its own API endpoints, causing 400 on POST/PUT/DELETE with Bearer auth.
        """
        try:
            from ckan.config.middleware.flask_app import csrf
            from ckan.views.api import api as api_blueprint
            csrf.exempt(api_blueprint)
            log.debug('Exempted CKAN API blueprint from CSRF protection')
        except (ImportError, AttributeError) as e:
            log.debug('Could not exempt API blueprint from CSRF: %s', e)
        return app

    def get_helpers(self):
        return {
            'oauth2_get_stored_token': self._get_stored_token_helper,
            'oauth2_refresh_token': self.oauth2helper.refresh_token,
        }

    def _get_stored_token_helper(self, user_name=None):
        """Template helper to get stored OAuth2 token for a user."""
        if not user_name:
            user_name = getattr(toolkit.g, 'user', None)
        if not user_name:
            return None
        try:
            return self.oauth2helper.get_stored_token(user_name)
        except Exception as e:
            log.error("Error getting stored token for user %s: %s", user_name, e)
            return None

    def _install_request_loader(self):
        """Override Flask-Login's request_loader to handle OAuth2 Bearer tokens.

        Must be called lazily (at first request time) because login_manager is
        created after make_middleware() runs in CKAN 2.11's flask_app.py.
        """
        from flask import current_app

        login_manager = current_app.login_manager
        plugin_ref = self

        @login_manager.request_loader
        def oauth2_load_user_from_request(request):
            """Flask-Login request_loader: validate Bearer token, fall back to CKAN API tokens."""
            apikey = request.headers.get(plugin_ref.authorization_header, '')

            if apikey:
                if apikey.startswith('Bearer '):
                    apikey = apikey[7:].strip()
                try:
                    token = {'access_token': apikey}
                    user_name, user_obj = plugin_ref.oauth2helper.identify(token)
                    if user_obj is None and user_name:
                        user_obj = model.User.by_name(user_name)
                    if user_obj is not None:
                        return user_obj
                except Exception as e:
                    log.debug('request_loader: OAuth2 identify failed: %s', e)

            # Fall back to CKAN's native API token handling
            try:
                from ckan.views import _get_user_for_apitoken
                return _get_user_for_apitoken()
            except ImportError:
                return None

    def identify(self):
        log.debug('identify')

        # Lazy installation of request_loader
        if not self._request_loader_installed and not self._request_loader_attempted:
            self._request_loader_attempted = True
            try:
                self._install_request_loader()
                self._request_loader_installed = True
            except Exception as e:
                log.error('Failed to install OAuth2 request_loader: %s', e)

        def _refresh_and_save_token(user_name):
            try:
                new_token = self.oauth2helper.refresh_token(user_name)
            except Exception as e:
                log.error('Token refresh failed for user %s: %s', user_name, e)
                new_token = None

            if new_token:
                toolkit.g.usertoken = new_token
            else:
                log.warning('Token refresh unsuccessful for user %s, logging out', user_name)
                toolkit.g.user = None
                toolkit.g.userobj = None
                toolkit.g.usertoken = None
                g.user = None
                logout_user()

        def _check_and_refresh_stored_token(user_name):
            """Check if stored token is expired and refresh if needed.
            Returns True if the user should be logged out."""
            if toolkit.g.usertoken and toolkit.g.usertoken.get('access_token') and self.oauth2helper.jwt_enable:
                is_expired, _ = self.oauth2helper.check_token_expiration(
                    toolkit.g.usertoken['access_token']
                )
                if is_expired:
                    log.info('Stored token expired for user %s, attempting refresh', user_name)
                    new_token = self.oauth2helper.refresh_token(user_name)
                    if new_token:
                        toolkit.g.usertoken = new_token
                    else:
                        log.warning('Stored token refresh failed for user %s, logging out', user_name)
                        toolkit.g.user = None
                        toolkit.g.userobj = None
                        toolkit.g.usertoken = None
                        g.user = None
                        logout_user()
                        return True
            return False

        apikey = toolkit.request.headers.get(self.authorization_header, '')

        if self.authorization_header == "authorization":
            if apikey.startswith('Bearer '):
                apikey = apikey[7:].strip()
            else:
                apikey = ''

        # If no bearer token and session is authenticated, use session
        if not apikey and current_user.is_authenticated:
            user_name = current_user.name
            g.user = user_name
            toolkit.g.user = user_name
            toolkit.g.userobj = model.User.by_name(user_name)
            toolkit.g.usertoken = self.oauth2helper.get_stored_token(user_name)
            toolkit.g.usertoken_refresh = partial(_refresh_and_save_token, user_name)
            login_user(toolkit.g.userobj)
            if _check_and_refresh_stored_token(user_name):
                return
            return

        # Bearer token authentication (takes precedence)
        user_name = None
        user_obj = None

        if apikey:
            try:
                token = {'access_token': apikey}
                user_name, user_obj = self.oauth2helper.identify(token)
            except Exception as e:
                log.warning('Bearer token auth error: %s: %s', type(e).__name__, e)

        # Fallback to session if API auth failed
        if user_name is None and current_user.is_authenticated:
            user_name = current_user.name
            log.info('User %s logged using session', user_name)

        # Set up user context if authenticated
        if user_name:
            g.user = user_name
            toolkit.g.user = user_name
            toolkit.g.userobj = user_obj if user_obj else model.User.by_name(user_name)
            toolkit.g.usertoken = self.oauth2helper.get_stored_token(user_name)
            login_user(toolkit.g.userobj)

            if not apikey:
                _check_and_refresh_stored_token(user_name)

            toolkit.g.usertoken_refresh = partial(_refresh_and_save_token, user_name)
        else:
            g.user = None
            toolkit.g.user = None
            toolkit.g.userobj = None
            log.warning('The user is not currently logged...')
