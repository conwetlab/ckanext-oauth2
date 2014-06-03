# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import ckanext.oauth2.repozewho as oauth2_repozewho

from pylons import config
from ckan import plugins
from ckan.plugins import toolkit

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

    def __init__(self, name=None):
        '''Store the OAuth 2 client configuration'''
        log.debug('Init')
        self.logout_url = config.get('ckan.oauth2.logout_url', '/user/logged_out')
        self.register_url = config.get('ckan.oauth2.register_url', None)
        self.reset_url = config.get('ckan.oauth2.reset_url', None)
        self.edit_url = config.get('ckan.oauth2.edit_url', None)

    def before_map(self, m):
        log.debug('Setting up the redirections to the OAuth2 service')

        # We need to handle petitions received to the Callback URL
        # since some error can arise and we need to process them
        m.connect(oauth2_repozewho.REDIRECT_URL,
                  controller='ckanext.oauth2.controller:OAuth2Controller',
                  action='callback')

        # Redirect the user to the OAuth service register page
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
        environ = toolkit.request.environ
        if 'repoze.who.identity' in environ:
            repoze_userid = environ['repoze.who.identity']['repoze.who.userid']
            log.debug('User logged %r' % repoze_userid)
            toolkit.c.user = repoze_userid
        else:
            log.warn('The user is not currently logged...')

    def login(self):
        log.debug('login')
        if not toolkit.c.user:
            # A 401 HTTP Status will cause the login to be triggered
            return toolkit.abort(401)
        redirect_to = toolkit.request.headers.get('Referer', '/')
        toolkit.redirect_to(bytes(redirect_to))

    def logout(self):
        log.debug('logout')
        environ = toolkit.request.environ

        if 'repoze.who.identity' in environ:
            repoze_userid = environ['repoze.who.identity']['repoze.who.userid']

            for plugin_name in environ['repoze.who.plugins']:
                plugin = environ['repoze.who.plugins'][plugin_name]
                if hasattr(plugin, 'forget'):
                    headers = plugin.forget(environ, repoze_userid)
                    for header, value in headers:
                        toolkit.response.headers.add(header, value)

        return toolkit.redirect_to(bytes(self.logout_url), locale='default')

    def get_auth_functions(self):
        # we need to prevent some actions being authorized.
        return {
            'user_create': user_create,
            'user_update': user_update,
            'user_reset': user_reset,
            'request_reset': request_reset,
        }
