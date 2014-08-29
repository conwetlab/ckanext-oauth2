# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ckan.model as model
import db
import json
import logging

from base64 import b64decode, b64encode
from repoze.who.interfaces import IIdentifier, IAuthenticator, IChallenger
from requests_oauthlib import OAuth2Session
from urlparse import urlparse
from webob import Request, Response
from zope.interface import implements

log = logging.getLogger(__name__)

REDIRECT_URL = '/oauth2/callback'
CAME_FROM_FIELD = 'came_from'
INITIAL_PAGE = '/dashboard'


def make_plugin(**kwargs):
    return OAuth2Plugin(**kwargs)


def generate_state(url):
    return b64encode(bytes(json.dumps({CAME_FROM_FIELD: url})))


def get_came_from(state):
    return json.loads(b64decode(state)).get(CAME_FROM_FIELD, '/')


class OAuth2Plugin(object):
    '''
    A repoze.who plugin to authenticate via OAuth2
    '''

    implements(IIdentifier, IChallenger, IAuthenticator)

    def __init__(self, authorization_endpoint=None, token_endpoint=None, client_id=None, client_secret=None,
                 scope=None, rememberer_name=None, profile_api_url=None, profile_api_user_field=None,
                 profile_api_fullname_field=None, profile_api_mail_field=None):

        # Check that all the required fields are provided
        if not authorization_endpoint or not token_endpoint or not client_id or not client_secret \
                or not profile_api_url or not profile_api_user_field:
            raise ValueError('authorization_endpoint, token_endpoint, client_id, client_secret parameters, '
                             'profile_api_url and profile_api_user_field are required')

        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope if scope is None else (scope.split(' ') if ' ' in scope else scope.split('\n'))
        self.rememberer_name = rememberer_name
        self.profile_api_url = profile_api_url
        self.profile_api_user_field = profile_api_user_field
        self.profile_api_fullname_field = profile_api_fullname_field
        self.profile_api_mail_field = profile_api_mail_field

        # Init db
        db.init_db(model)

    def _redirect_uri(self, request):
        return ''.join([request.host_url, REDIRECT_URL])

    def challenge(self, environ, status, app_headers=(), forget_headers=()):
        '''Challenge for OAuth2 credentials.

        Redirect the user through the OAuth2 login process.  Once complete
        it will post the obtained BrowserID assertion to the configured
        postback URL.

        The user will be only redirected on login attemps.
        '''
        log.debug('Repoze OAuth challenge')
        request = Request(environ)

        if request.path == '/user/login':
            # Only log the user when s/he tries to log in. Otherwise, the user will
            # be redirected to the main page where an error will be shown
            came_from_url = request.headers.get('Referer', INITIAL_PAGE)
            came_from_url_parsed = urlparse(came_from_url)

            # Avoid redirecting to external hosts when a user logs in
            if came_from_url_parsed.netloc != '' and came_from_url_parsed.netloc != request.host:
                came_from_url = INITIAL_PAGE

            # When referer == HOME or referer == LOGOUT_PAGE, redirect the user to the dashboard
            pages = ['/', '/user/logged_out_redirect']
            if came_from_url_parsed.path in pages:
                came_from_url = INITIAL_PAGE

            came_from_url = INITIAL_PAGE if came_from_url_parsed.netloc != '' and came_from_url_parsed.netloc != request.host else came_from_url
            state = generate_state(came_from_url)
            oauth = OAuth2Session(self.client_id, redirect_uri=self._redirect_uri(request), scope=self.scope, state=state)
            auth_url, _ = oauth.authorization_url(self.authorization_endpoint)
            location = auth_url
            log.debug('Challenge: Redirecting challenge to page {0}'.format(auth_url))
        else:
            location = request.headers.get('Referer', '/')
            url_parsed = urlparse(location)

            if url_parsed.netloc != request.host or location == request.url:
                # When the referer is another web site, the user must be redirected to the home page
                # When the referer is the same than the requested page, the user must be redirected to the home page
                location = '/'

            log.debug('User is trying to access to an Unauthorized function %r' % request.path)

        response = Response()
        response.status = 302
        response.location = location
        return response

    def identify(self, environ):
        '''
        Extract OAuth2 credentials from request

        This function is executed on each request. However, we only use it when the OAuth2
        Callback is called. Otherwise None is returned.
        '''
        log.debug('Repoze OAuth identify')
        request = Request(environ)

        # Only execute this function when /oauth2/callback is called
        if request.path != REDIRECT_URL:
            return None

        try:
            # On succed, the authenticate function will execute
            state = request.params.get('state')
            came_from = get_came_from(state)
            oauth = OAuth2Session(self.client_id, redirect_uri=self._redirect_uri(request), scope=self.scope)
            token = oauth.fetch_token(self.token_endpoint,
                                      client_secret=self.client_secret,
                                      authorization_response=request.url)
            return {'oauth2.token': token, CAME_FROM_FIELD: came_from}
        except Exception as e:
            log.error('The OAuth2 login fails: %r' % e)
            return None

    def authenticate(self, environ, identity):
        '''
        Authenticate and extract identity from OAuth2 tokens

        This function is executed inmediatly after when the identify function returns
        something different from None: /oauth2/callback is called with the required parameteres

        Please note, if this function does not override the property "repoze.who.application"
        of the environ, the OAuth2 Callback controller will be executed. We relay in the
        _redirect_from_callback function to do so.
        '''
        request = Request(environ)
        log.debug('Repoze OAuth authenticate')
        if 'oauth2.token' in identity:
            oauth = OAuth2Session(self.client_id, token=identity['oauth2.token'])
            profile_response = oauth.get(self.profile_api_url)
            user_data = profile_response.json()
            email = user_data[self.profile_api_mail_field]          # WARN: profile_api_mail_field should be defined!!
            user_name = user_data[self.profile_api_user_field]      # WARN: profile_api_user_field should be defined!!
            user = None
            users = model.User.by_email(email)  # It returns a list of users (since it can exist some users with the same email...)
            if len(users) == 1:                 # In the Fi-Ware case this problem does not exist since all the users have different mails...
                user = users[0]

            # If the user does not exist, we have to create it...
            if user is None:
                user = model.User(email=email)

            # Now we update his/her user_name with the one provided by the OAuth2 service
            # In the future, users will be obtained based on this field
            user.name = user_name

            # Update fullname
            if self.profile_api_fullname_field and self.profile_api_fullname_field in user_data:
                user.fullname = user_data[self.profile_api_fullname_field]

            # Update mail
            # if self.profile_api_mail_field and self.profile_api_mail_field in user_data:
            #     user.email = user_data[self.profile_api_mail_field]

            # Update token
            self.update_token(user_name, identity['oauth2.token'])

            # Save the user in the database
            model.Session.add(user)
            model.Session.commit()
            model.Session.remove()

            identity.update({'repoze.who.userid': user.name})
            self._redirect_from_callback(request, identity)
            return user.name
        return None

    def _get_rememberer(self, environ):
        plugins = environ.get('repoze.who.plugins', {})
        return plugins.get(self.rememberer_name)

    def remember(self, environ, identity):
        '''
        Remember the authenticated identity.

        This method simply delegates to another IIdentifier plugin if configured.
        '''
        log.debug('Repoze OAuth remember')
        rememberer = self._get_rememberer(environ)
        return rememberer.remember(environ, identity)

    def forget(self, environ, identity):
        '''
        Forget the authenticated identity.

        This method simply delegates to another IIdentifier plugin if configured.
        '''
        log.debug('Repoze OAuth forget')
        rememberer = self._get_rememberer(environ)
        return rememberer.forget(environ, identity)

    def _redirect_from_callback(self, request, identity):
        '''Redirect from the callback URL after a successful authentication.'''
        if request.path == REDIRECT_URL:
            came_from = identity.get(CAME_FROM_FIELD, INITIAL_PAGE)
            response = Response()
            response.status = 302
            response.location = came_from
            request.environ['repoze.who.application'] = response

    def get_token(self, user_name):
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
        token = self.get_token(user_name)
        if token:
            client = OAuth2Session(self.client_id, token=token, scope=self.scope)
            token = client.refresh_token(self.token_endpoint, client_secret=self.client_secret, client_id=self.client_id)
            self.update_token(user_name, token)
            log.info('Token for user %s has been updated properly' % user_name)
            return token
        else:
            log.warn('User %s has no refresh token' % user_name)
