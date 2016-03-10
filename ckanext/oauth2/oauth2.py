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

import ckan.model as model
import constants
import db
import json
import logging

from base64 import b64encode, b64decode
from ckan.plugins import toolkit
from pylons import config
from requests_oauthlib import OAuth2Session

log = logging.getLogger(__name__)


def generate_state(url):
    return b64encode(bytes(json.dumps({constants.CAME_FROM_FIELD: url})))


def get_came_from(state):
    return json.loads(b64decode(state)).get(constants.CAME_FROM_FIELD, '/')


class OAuth2Helper(object):

    def __init__(self):

        self.authorization_endpoint = config.get('ckan.oauth2.authorization_endpoint', None)
        self.token_endpoint = config.get('ckan.oauth2.token_endpoint', None)
        self.profile_api_url = config.get('ckan.oauth2.profile_api_url', None)
        self.client_id = config.get('ckan.oauth2.client_id', None)
        self.client_secret = config.get('ckan.oauth2.client_secret', None)
        self.scope = config.get('ckan.oauth2.scope', '').decode()
        self.rememberer_name = config.get('ckan.oauth2.rememberer_name', None)
        self.profile_api_user_field = config.get('ckan.oauth2.profile_api_user_field', None)
        self.profile_api_fullname_field = config.get('ckan.oauth2.profile_api_fullname_field', None)
        self.profile_api_mail_field = config.get('ckan.oauth2.profile_api_mail_field', None)
        self.profile_api_groupmembership_field = config.get('ckan.oauth2.profile_api_groupmembership_field', None)
        self.sysadmin_group_name = config.get('ckan.oauth2.sysadmin_group_name', None)


        # Init db
        db.init_db(model)

        if not self.authorization_endpoint or not self.token_endpoint or not self.client_id or not self.client_secret \
                or not self.profile_api_url or not self.profile_api_user_field:
            raise ValueError('authorization_endpoint, token_endpoint, client_id, client_secret, '
                             'profile_api_url and profile_api_user_field are required')

    def _redirect_uri(self, request):
        return ''.join([request.host_url, constants.REDIRECT_URL])

    def challenge(self, came_from_url):
        # This function is called by the log in function when the user is not logged in
        state = generate_state(came_from_url)
        oauth = OAuth2Session(self.client_id, redirect_uri=self._redirect_uri(toolkit.request), scope=self.scope, state=state)
        auth_url, _ = oauth.authorization_url(self.authorization_endpoint)
        toolkit.response.status = 302
        toolkit.response.location = auth_url
        log.debug('Challenge: Redirecting challenge to page {0}'.format(auth_url))

    def get_token(self):
        oauth = OAuth2Session(self.client_id, redirect_uri=self._redirect_uri(toolkit.request), scope=self.scope)
        token = oauth.fetch_token(self.token_endpoint,
                                  client_secret=self.client_secret,
                                  authorization_response=toolkit.request.url)
        return token

    def identify(self, token):
        oauth = OAuth2Session(self.client_id, token=token)
        profile_response = oauth.get(self.profile_api_url)

        # Token can be invalid
        if not profile_response.ok:
            error = profile_response.json()
            if error.get('error', '') == 'invalid_token':
                raise ValueError(error.get('error_description'))
            else:
                profile_response.raise_for_status()
        else:
            user_data = profile_response.json()
            user_name = user_data[self.profile_api_user_field]
            user = model.User.by_name(user_name)

            if user is None:
                # If the user does not exist, it's created
                user = model.User(name=user_name)

            # Update fullname
            if self.profile_api_fullname_field and self.profile_api_fullname_field in user_data:
                user.fullname = user_data[self.profile_api_fullname_field]

            # Update mail
            if self.profile_api_mail_field and self.profile_api_mail_field in user_data:
                user.email = user_data[self.profile_api_mail_field]

             # Update sysadmin status
            if self.profile_api_groupmembership_field and self.profile_api_groupmembership_field in user_data:
                if self.sysadmin_group_name and self.sysadmin_group_name in user_data[self.profile_api_groupmembership_field]:
                    user.sysadmin = True
                else:
                    user.sysadmin = False

            # Save the user in the database
            model.Session.add(user)
            model.Session.commit()
            model.Session.remove()

            return user.name

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
        state = toolkit.request.params.get('state')
        came_from = get_came_from(state)
        toolkit.response.status = 302
        toolkit.response.location = came_from

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
        user_token.refresh_token = token['refresh_token']
        user_token.expires_in = token['expires_in']
        model.Session.add(user_token)
        model.Session.commit()

    def refresh_token(self, user_name):
        token = self.get_stored_token(user_name)
        if token:
            client = OAuth2Session(self.client_id, token=token, scope=self.scope)
            token = client.refresh_token(self.token_endpoint, client_secret=self.client_secret, client_id=self.client_id)
            self.update_token(user_name, token)
            log.info('Token for user %s has been updated properly' % user_name)
            return token
        else:
            log.warn('User %s has no refresh token' % user_name)
