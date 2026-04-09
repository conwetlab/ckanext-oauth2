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


import base64
import ckan.model as model
import json
import logging
import os
from base64 import b64encode, b64decode
from urllib.parse import urljoin

from ckan.plugins import toolkit
from oauthlib.oauth2 import InsecureTransportError
import requests
from requests_oauthlib import OAuth2Session

import jwt

from ckanext.oauth2 import constants
from ckanext.oauth2 import db


log = logging.getLogger(__name__)


def generate_state(url):
    return b64encode(json.dumps({constants.CAME_FROM_FIELD: url}).encode('utf-8')).decode('utf-8')


def get_came_from(state):
    if isinstance(state, str):
        state = state.encode('utf-8')
    return json.loads(b64decode(state)).get(constants.CAME_FROM_FIELD, '/')


REQUIRED_CONF = ("authorization_endpoint", "token_endpoint", "client_id", "client_secret", "profile_api_url", "profile_api_user_field", "profile_api_mail_field")


class OAuth2Helper(object):

    def __init__(self):

        self.verify_https = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '') == ""
        if self.verify_https and os.environ.get("REQUESTS_CA_BUNDLE", "").strip() != "":
            self.verify_https = os.environ["REQUESTS_CA_BUNDLE"].strip()

        self.jwt_enable = str(os.environ.get('CKAN_OAUTH2_JWT_ENABLE', toolkit.config.get('ckan.oauth2.jwt.enable', ''))).strip().lower() in ("true", "1", "on")

        self.legacy_idm = str(os.environ.get('CKAN_OAUTH2_LEGACY_IDM', toolkit.config.get('ckan.oauth2.legacy_idm', ''))).strip().lower() in ("true", "1", "on")
        self.authorization_endpoint = str(os.environ.get('CKAN_OAUTH2_AUTHORIZATION_ENDPOINT', toolkit.config.get('ckan.oauth2.authorization_endpoint', ''))).strip()
        self.token_endpoint = str(os.environ.get('CKAN_OAUTH2_TOKEN_ENDPOINT', toolkit.config.get('ckan.oauth2.token_endpoint', ''))).strip()
        self.profile_api_url = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_URL', toolkit.config.get('ckan.oauth2.profile_api_url', ''))).strip()
        self.client_id = str(os.environ.get('CKAN_OAUTH2_CLIENT_ID', toolkit.config.get('ckan.oauth2.client_id', ''))).strip()
        self.client_secret = str(os.environ.get('CKAN_OAUTH2_CLIENT_SECRET', toolkit.config.get('ckan.oauth2.client_secret', ''))).strip()
        self.scope = str(os.environ.get('CKAN_OAUTH2_SCOPE', toolkit.config.get('ckan.oauth2.scope', ''))).strip()
        self.rememberer_name = str(os.environ.get('CKAN_OAUTH2_REMEMBER_NAME', toolkit.config.get('ckan.oauth2.rememberer_name', 'auth_tkt'))).strip()
        self.profile_api_user_field = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_USER_FIELD', toolkit.config.get('ckan.oauth2.profile_api_user_field', ''))).strip()
        self.profile_api_fullname_field = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_FULLNAME_FIELD', toolkit.config.get('ckan.oauth2.profile_api_fullname_field', ''))).strip()
        self.profile_api_mail_field = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_MAIL_FIELD', toolkit.config.get('ckan.oauth2.profile_api_mail_field', ''))).strip()
        self.profile_api_groupmembership_field = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_GROUPMEMBERSHIP_FIELD', toolkit.config.get('ckan.oauth2.profile_api_groupmembership_field', ''))).strip()
        self.sysadmin_group_name = str(os.environ.get('CKAN_OAUTH2_SYSADMIN_GROUP_NAME', toolkit.config.get('ckan.oauth2.sysadmin_group_name', ''))).strip()

        self.redirect_uri = urljoin(urljoin(toolkit.config.get('ckan.site_url', 'http://localhost:5000'), toolkit.config.get('ckan.root_path')), constants.REDIRECT_URL)

        # Init db
        db.init_db(model)

        missing = [key for key in REQUIRED_CONF if getattr(self, key, "") == ""]
        if missing:
            raise ValueError("Missing required oauth2 conf: %s" % ", ".join(missing))
        elif self.scope == "":
            self.scope = None

    def challenge(self, came_from_url):
        state = generate_state(came_from_url)
        oauth = OAuth2Session(self.client_id, redirect_uri=self.redirect_uri, scope=self.scope, state=state)
        auth_url, _ = oauth.authorization_url(self.authorization_endpoint)
        log.debug('Challenge: Redirecting challenge to page {0}'.format(auth_url))
        return toolkit.redirect_to(auth_url)

    def get_token(self):
        oauth = OAuth2Session(self.client_id, redirect_uri=self.redirect_uri, scope=self.scope)

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        if self.legacy_idm:
            headers['Authorization'] = 'Basic %s' % base64.urlsafe_b64encode(
                ('%s:%s' % (self.client_id, self.client_secret)).encode('utf-8')
            ).decode('utf-8')

        try:
            token = oauth.fetch_token(self.token_endpoint,
                                      headers=headers,
                                      client_secret=self.client_secret,
                                      authorization_response=toolkit.request.url,
                                      verify=self.verify_https)
        except requests.exceptions.SSLError as e:
            if "verify failed" in str(e):
                raise InsecureTransportError()
            else:
                raise

        return token

    def identify(self, token):

        if self.jwt_enable:
            access_token = token['access_token']
            user_data = jwt.decode(access_token, options={"verify_signature": False}, algorithms=["HS256", "RS256"])
            user = self.user_json(user_data)
        else:

            try:
                if self.legacy_idm:
                    profile_response = requests.get(self.profile_api_url + '?access_token=%s' % token['access_token'], verify=self.verify_https)
                else:
                    oauth = OAuth2Session(self.client_id, token=token)
                    profile_response = oauth.get(self.profile_api_url, verify=self.verify_https)

            except requests.exceptions.SSLError as e:
                if "verify failed" in str(e):
                    raise InsecureTransportError()
                else:
                    raise

            # Token can be invalid
            if not profile_response.ok:
                error = profile_response.json()
                if error.get('error', '') == 'invalid_token':
                    raise ValueError(error.get('error_description'))
                else:
                    profile_response.raise_for_status()
            else:
                user_data = profile_response.json()
                user = self.user_json(user_data)

        # Save the user in the database
        model.Session.add(user)
        model.Session.commit()
        model.Session.remove()

        return user.name

    def user_json(self, user_data):
        email = user_data[self.profile_api_mail_field]
        user_name = user_data[self.profile_api_user_field]

        # In CKAN can exists more than one user associated with the same email
        # Some providers, like Google and FIWARE only allows one account per email
        user = None
        users = model.User.by_email(email)
        if len(users) == 1:
            user = users[0]

        # If the user does not exist, we have to create it...
        if user is None:
            user = model.User(email=email)

        # Now we update his/her user_name with the one provided by the OAuth2 service
        # In the future, users will be obtained based on this field
        user.name = user_name

        # Update fullname
        if self.profile_api_fullname_field != "" and self.profile_api_fullname_field in user_data:
            user.fullname = user_data[self.profile_api_fullname_field]

        # Update sysadmin status
        if self.profile_api_groupmembership_field != "" and self.profile_api_groupmembership_field in user_data:
            user.sysadmin = self.sysadmin_group_name in user_data[self.profile_api_groupmembership_field]

        return user

    def _get_rememberer(self, environ):
        plugins = environ.get('repoze.who.plugins', {})
        return plugins.get(self.rememberer_name)

    def remember(self, user_name):
        '''
        Remember the authenticated identity.

        This method simply delegates to another IIdentifier plugin if configured.
        '''
        log.debug('Repoze OAuth remember')
        environ = toolkit.request.environ
        rememberer = self._get_rememberer(environ)
        identity = {'repoze.who.userid': user_name}
        headers = rememberer.remember(environ, identity)
        for header, value in headers:
            toolkit.response.headers.add(header, value)

    def redirect_from_callback(self):
        '''Redirect to the callback URL after a successful authentication.'''
        state = toolkit.request.args.get('state')
        came_from = get_came_from(state)
        return toolkit.redirect_to(came_from)

    def get_stored_token(self, user_name):
        user_token = db.UserToken.by_user_name(user_name=user_name)
        if user_token:
            return {
                'access_token': user_token.access_token,
                'refresh_token': user_token.refresh_token,
                'expires_in': user_token.expires_in,
                'token_type': user_token.token_type
            }

    def update_token(self, user_name, token):

        user_token = db.UserToken.by_user_name(user_name=user_name)
        # Create the user if it does not exist
        if not user_token:
            user_token = db.UserToken()
            user_token.user_name = user_name
        # Save the new token
        user_token.access_token = token['access_token']
        user_token.token_type = token['token_type']
        user_token.refresh_token = token.get('refresh_token')
        if 'expires_in' in token:
            user_token.expires_in = token['expires_in']
        else:
            access_token = jwt.decode(user_token.access_token, options={"verify_signature": False}, algorithms=["HS256", "RS256"])
            user_token.expires_in = access_token['exp'] - access_token['iat']

        model.Session.add(user_token)
        model.Session.commit()

    def refresh_token(self, user_name):
        token = self.get_stored_token(user_name)
        if token:
            client = OAuth2Session(self.client_id, token=token, scope=self.scope)
            try:
                token = client.refresh_token(self.token_endpoint, client_secret=self.client_secret, client_id=self.client_id, verify=self.verify_https)
            except requests.exceptions.SSLError as e:
                if "verify failed" in str(e):
                    raise InsecureTransportError()
                else:
                    raise
            self.update_token(user_name, token)
            log.info('Token for user %s has been updated properly' % user_name)
            return token
        else:
            log.warning('User %s has no refresh token' % user_name)
