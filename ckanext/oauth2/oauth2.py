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
import json
import logging
import os
from base64 import b64encode, b64decode
from urllib.parse import urljoin

import ckan.model as model
from ckan.plugins import toolkit
from flask_login import login_user
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
    if not state:
        return '/'
    if isinstance(state, str):
        state = state.encode('utf-8')
    return json.loads(b64decode(state)).get(constants.CAME_FROM_FIELD, '/')


REQUIRED_CONF = (
    "authorization_endpoint", "token_endpoint", "client_id",
    "client_secret", "profile_api_url", "profile_api_user_field",
    "profile_api_mail_field",
)


class OAuth2Helper(object):

    def __init__(self):

        self.verify_https = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '') == ""
        if self.verify_https and os.environ.get("REQUESTS_CA_BUNDLE", "").strip() != "":
            self.verify_https = os.environ["REQUESTS_CA_BUNDLE"].strip()

        self.jwt_enable = str(os.environ.get('CKAN_OAUTH2_JWT_ENABLE', toolkit.config.get('ckan.oauth2.jwt.enable', ''))).strip().lower() in ("true", "1", "on")

        # JWT configuration
        self.jwt_algorithm = str(os.environ.get('CKAN_OAUTH2_JWT_ALGORITHM', toolkit.config.get('ckan.oauth2.jwt.algorithm', 'HS256'))).strip()

        jwt_secret = str(os.environ.get('CKAN_OAUTH2_JWT_SECRET', toolkit.config.get('ckan.oauth2.jwt.secret', ''))).strip()
        self.jwt_secret = jwt_secret if jwt_secret else None

        jwt_public_key = str(os.environ.get('CKAN_OAUTH2_JWT_PUBLIC_KEY', toolkit.config.get('ckan.oauth2.jwt.public_key', ''))).strip()
        if jwt_public_key:
            # Handle escaped newlines in environment variables (PEM format)
            self.jwt_public_key = jwt_public_key.replace('\\n', '\n')
        else:
            self.jwt_public_key = None

        self.jwt_username_field = str(os.environ.get('CKAN_OAUTH2_JWT_USERNAME_FIELD', toolkit.config.get('ckan.oauth2.jwt.username_field', 'username'))).strip()
        self.jwt_email_field = str(os.environ.get('CKAN_OAUTH2_JWT_EMAIL_FIELD', toolkit.config.get('ckan.oauth2.jwt.email_field', 'email'))).strip()
        self.jwt_fullname_field = str(os.environ.get('CKAN_OAUTH2_JWT_FULLNAME_FIELD', toolkit.config.get('ckan.oauth2.jwt.fullname_field', 'name'))).strip()

        # OAuth2 configuration
        self.legacy_idm = str(os.environ.get('CKAN_OAUTH2_LEGACY_IDM', toolkit.config.get('ckan.oauth2.legacy_idm', ''))).strip().lower() in ("true", "1", "on")
        self.authorization_endpoint = str(os.environ.get('CKAN_OAUTH2_AUTHORIZATION_ENDPOINT', toolkit.config.get('ckan.oauth2.authorization_endpoint', ''))).strip()
        self.token_endpoint = str(os.environ.get('CKAN_OAUTH2_TOKEN_ENDPOINT', toolkit.config.get('ckan.oauth2.token_endpoint', ''))).strip()
        self.profile_api_url = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_URL', toolkit.config.get('ckan.oauth2.profile_api_url', ''))).strip()
        self.client_id = str(os.environ.get('CKAN_OAUTH2_CLIENT_ID', toolkit.config.get('ckan.oauth2.client_id', ''))).strip()
        self.client_secret = str(os.environ.get('CKAN_OAUTH2_CLIENT_SECRET', toolkit.config.get('ckan.oauth2.client_secret', ''))).strip()
        self.scope = str(os.environ.get('CKAN_OAUTH2_SCOPE', toolkit.config.get('ckan.oauth2.scope', ''))).strip()
        self.profile_api_user_field = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_USER_FIELD', toolkit.config.get('ckan.oauth2.profile_api_user_field', ''))).strip()
        self.profile_api_fullname_field = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_FULLNAME_FIELD', toolkit.config.get('ckan.oauth2.profile_api_fullname_field', ''))).strip()
        self.profile_api_mail_field = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_MAIL_FIELD', toolkit.config.get('ckan.oauth2.profile_api_mail_field', ''))).strip()
        self.profile_api_groupmembership_field = str(os.environ.get('CKAN_OAUTH2_PROFILE_API_GROUPMEMBERSHIP_FIELD', toolkit.config.get('ckan.oauth2.profile_api_groupmembership_field', ''))).strip()
        self.sysadmin_group_name = str(os.environ.get('CKAN_OAUTH2_SYSADMIN_GROUP_NAME', toolkit.config.get('ckan.oauth2.sysadmin_group_name', ''))).strip()

        # Response unwrapping for non-standard providers
        self.profile_response_path = str(os.environ.get('CKAN_OAUTH2_PROFILE_RESPONSE_PATH', toolkit.config.get('ckan.oauth2.profile_response_path', ''))).strip() or None
        self.token_response_path = str(os.environ.get('CKAN_OAUTH2_TOKEN_RESPONSE_PATH', toolkit.config.get('ckan.oauth2.token_response_path', ''))).strip() or None
        self.token_response_key = str(os.environ.get('CKAN_OAUTH2_TOKEN_RESPONSE_KEY', toolkit.config.get('ckan.oauth2.token_response_key', 'access_token'))).strip()

        self.redirect_uri = urljoin(urljoin(toolkit.config.get('ckan.site_url', 'http://localhost:5000'), toolkit.config.get('ckan.root_path')), constants.REDIRECT_URL)

        # Init db
        db.init_db()

        missing = [key for key in REQUIRED_CONF if getattr(self, key, "") == ""]
        if missing:
            raise ValueError("Missing required oauth2 conf: %s" % ", ".join(missing))
        elif self.scope == "":
            self.scope = None

    def _unwrap_response(self, data, path):
        """Unwrap a nested API response by following a dot-separated path."""
        if not path:
            return data
        for key in path.split('.'):
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                log.warning('_unwrap_response: key "%s" not found (path: %s)', key, path)
                return data
        return data

    def _compliance_fix(self, session):
        """Apply compliance hooks for non-standard OAuth2 providers."""
        def _fix_access_token(response):
            if not self.token_response_path:
                return response
            data = response.json()
            unwrapped = self._unwrap_response(data, self.token_response_path)
            if self.token_response_key and self.token_response_key in unwrapped:
                response._content = json.dumps(unwrapped[self.token_response_key]).encode('utf-8')
            return response

        session.register_compliance_hook('access_token_response', _fix_access_token)
        return session

    def _decode_jwt(self, token, verify=True):
        """Decode a JWT token with optional signature verification.

        Args:
            token: The JWT token string.
            verify: If True, verify the signature using the configured algorithm and key.

        Returns:
            dict: The decoded JWT claims.
        """
        log.debug("_decode_jwt: verify=%s, algorithm=%s", verify, self.jwt_algorithm)
        try:
            if verify:
                if self.jwt_algorithm.startswith('HS'):
                    if not self.jwt_secret:
                        raise ValueError('JWT secret not configured for symmetric algorithm %s' % self.jwt_algorithm)
                    return jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                elif self.jwt_algorithm.startswith(('RS', 'ES')):
                    if not self.jwt_public_key:
                        raise ValueError('JWT public key not configured for asymmetric algorithm %s' % self.jwt_algorithm)
                    return jwt.decode(token, self.jwt_public_key, algorithms=[self.jwt_algorithm])
                else:
                    raise ValueError('Unknown JWT algorithm: %s' % self.jwt_algorithm)
            else:
                return jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        except jwt.ExpiredSignatureError:
            log.warning('JWT token expired')
            raise
        except jwt.InvalidSignatureError as e:
            log.error('JWT signature verification failed: %s', e)
            raise
        except (jwt.DecodeError, jwt.InvalidTokenError) as e:
            log.error('JWT decode error (%s): %s', type(e).__name__, e)
            raise

    def check_token_expiration(self, access_token):
        """Check if a JWT token is expired without raising.

        Returns:
            tuple: (is_expired: bool, username: str | None)
        """
        try:
            claims = self._decode_jwt(access_token, verify=True)
            username = claims.get(self.jwt_username_field)
            return False, username
        except jwt.ExpiredSignatureError:
            claims = self._decode_jwt(access_token, verify=False)
            username = claims.get(self.jwt_username_field)
            return True, username

    def challenge(self, came_from_url):
        state = generate_state(came_from_url)
        oauth = OAuth2Session(self.client_id, redirect_uri=self.redirect_uri, scope=self.scope, state=state)
        oauth = self._compliance_fix(oauth)
        auth_url, _ = oauth.authorization_url(self.authorization_endpoint)
        log.debug('Challenge: Redirecting challenge to page %s', auth_url)
        return toolkit.redirect_to(auth_url)

    def get_token(self):
        oauth = OAuth2Session(self.client_id, redirect_uri=self.redirect_uri, scope=self.scope)
        oauth = self._compliance_fix(oauth)

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
        """Identify a user from an OAuth2 token.

        Returns:
            tuple: (user_name, user_obj) — the username string and the CKAN User object.
        """
        user_profile = {}

        if self.jwt_enable:
            access_token = token['access_token']
            jwt_profile = self._get_profile_from_jwt(access_token)
            user_profile.update(jwt_profile)

        # Fetch profile from API to get complementary information
        try:
            api_profile = self._get_profile_from_api(token)
            # API data does not override JWT data
            for key, value in api_profile.items():
                if key not in user_profile:
                    user_profile[key] = value
        except Exception as e:
            if not self.jwt_enable:
                raise
            log.warning("Failed to fetch profile from API: %s. Continuing with JWT data only.", e)

        user = self._user_from_profile(user_profile)

        # Save the user in the database
        model.Session.add(user)
        model.Session.commit()
        model.Session.remove()

        return user.name, user

    def _get_profile_from_jwt(self, access_token):
        """Extract user profile fields from JWT token claims."""
        has_key = (self.jwt_algorithm.startswith('HS') and self.jwt_secret) or \
                  (self.jwt_algorithm.startswith(('RS', 'ES')) and self.jwt_public_key)

        if has_key:
            token_decoded = self._decode_jwt(access_token, verify=True)
        else:
            token_decoded = self._decode_jwt(access_token, verify=False)

        profile = {}
        if self.jwt_username_field and self.jwt_username_field in token_decoded:
            profile[self.profile_api_user_field] = token_decoded[self.jwt_username_field]
        if self.jwt_email_field and self.jwt_email_field in token_decoded:
            profile[self.profile_api_mail_field] = token_decoded[self.jwt_email_field]
        if self.jwt_fullname_field and self.jwt_fullname_field in token_decoded:
            profile[self.profile_api_fullname_field] = token_decoded[self.jwt_fullname_field]

        return profile

    def _get_profile_from_api(self, token):
        """Fetch user profile from the OAuth2 profile API endpoint."""
        try:
            if self.legacy_idm:
                profile_response = requests.get(
                    self.profile_api_url + '?access_token=%s' % token['access_token'],
                    verify=self.verify_https,
                )
            else:
                oauth = OAuth2Session(self.client_id, token=token)
                profile_response = oauth.get(self.profile_api_url, verify=self.verify_https)
        except requests.exceptions.SSLError as e:
            if "verify failed" in str(e):
                raise InsecureTransportError()
            else:
                raise

        if not profile_response.ok:
            error = profile_response.json()
            if error.get('error', '') == 'invalid_token':
                raise ValueError(error.get('error_description'))
            else:
                profile_response.raise_for_status()

        user_data = profile_response.json()
        return self._unwrap_response(user_data, self.profile_response_path) if self.profile_response_path else user_data

    def _user_from_profile(self, user_data):
        """Find or create a CKAN user from profile data."""
        email = user_data[self.profile_api_mail_field]
        user_name = user_data[self.profile_api_user_field]

        user = None
        users = model.User.by_email(email)
        if len(users) == 1:
            user = users[0]

        if user is None:
            user = model.User(email=email)

        user.name = user_name

        if self.profile_api_fullname_field and self.profile_api_fullname_field in user_data:
            user.fullname = user_data[self.profile_api_fullname_field]

        if self.profile_api_groupmembership_field and self.profile_api_groupmembership_field in user_data:
            user.sysadmin = self.sysadmin_group_name in user_data[self.profile_api_groupmembership_field]

        return user

    def log_user_into_ckan(self, user_obj):
        """Log the user into CKAN using Flask-Login."""
        login_user(user_obj)

    def redirect_from_callback(self):
        """Redirect to the callback URL after a successful authentication."""
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
        if not user_token:
            user_token = db.UserToken()
            user_token.user_name = user_name

        user_token.access_token = token['access_token']
        user_token.token_type = token['token_type']
        user_token.refresh_token = token.get('refresh_token')

        if 'expires_in' in token:
            user_token.expires_in = token['expires_in']
        else:
            try:
                access_token = self._decode_jwt(user_token.access_token, verify=False)
                user_token.expires_in = access_token['exp'] - access_token['iat']
            except Exception:
                log.warning('Could not extract expires_in from JWT token')

        model.Session.add(user_token)
        model.Session.commit()

    def refresh_token(self, user_name):
        token = self.get_stored_token(user_name)
        if token:
            client = OAuth2Session(self.client_id, token=token, scope=self.scope)
            client = self._compliance_fix(client)
            try:
                token = client.refresh_token(
                    self.token_endpoint,
                    client_secret=self.client_secret,
                    client_id=self.client_id,
                    verify=self.verify_https,
                )
            except requests.exceptions.SSLError as e:
                if "verify failed" in str(e):
                    raise InsecureTransportError()
                else:
                    raise
            except Exception as e:
                log.error('Failed to refresh token for user %s: %s', user_name, e)
                return None
            self.update_token(user_name, token)
            log.info('Token for user %s has been updated properly', user_name)
            return token
        else:
            log.warning('User %s has no refresh token', user_name)
            return None
