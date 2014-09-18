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

import ckanext.oauth2.repozewho as oauth2_repozewho
import logging
import oauth2

from functools import partial
from ckan import plugins
from ckan.common import session
from ckan.plugins import toolkit
from pylons import config

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

        self.oauth2helper = oauth2.OAuth2Helper()

    def before_map(self, m):
        log.debug('Setting up the redirections to the OAuth2 service')

        # We need to handle petitions received to the Callback URL
        # since some error can arise and we need to process them
        m.connect(oauth2_repozewho.REDIRECT_URL,
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

        # Create session if it does not exist. Workaround to show flash messages
        session.save()

        def _refresh_and_save_token(user_name):
            new_token = self.oauth2helper.refresh_token(user_name)
            if new_token:
                toolkit.c.usertoken = new_token

        environ = toolkit.request.environ
        if 'repoze.who.identity' in environ:
            repoze_userid = environ['repoze.who.identity']['repoze.who.userid']
            log.debug('User logged %r' % repoze_userid)
            toolkit.c.user = repoze_userid
            toolkit.c.usertoken = self.oauth2helper.get_stored_token(repoze_userid)
            toolkit.c.usertoken_refresh = partial(_refresh_and_save_token, repoze_userid)
        else:
            log.warn('The user is not currently logged...')

    def login(self):
        log.debug('login')
        
        if not toolkit.c.user:
            self.oauth2helper.challange()
        else:
            redirect_to = toolkit.request.headers.get('Referer', '/')
            toolkit.redirect_to(bytes(redirect_to))

    def get_auth_functions(self):
        # we need to prevent some actions being authorized.
        return {
            'user_create': user_create,
            'user_update': user_update,
            'user_reset': user_reset,
            'request_reset': request_reset,
        }

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        plugins.toolkit.add_template_directory(config, 'templates')
