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

import logging
import oauth2

import ckan.lib.helpers as helpers
import ckan.lib.base as base

from ckanext.oauth2.plugin import toolkit


log = logging.getLogger(__name__)


class OAuth2Controller(base.BaseController):

    def __init__(self):
        self.oauth2helper = oauth2.OAuth2Helper()

    def callback(self):
        try:
            token = self.oauth2helper.identify()
            identity = self.oauth2helper.authenticate(token)
            user_name = identity['repoze.who.userid']
            self.oauth2helper.remember(identity)
            self.oauth2helper.update_token(user_name, token['oauth2.token'])
            self.oauth2helper.redirect_from_callback(identity)
        except Exception as e:
            # If the callback is called with an error, we must show the message
            error_description = toolkit.request.GET.get('error_description')
            if not error_description:
                error_description = e.message

            toolkit.response.status_int = 302
            redirect_url = oauth2.get_came_from(toolkit.request.params.get('state'))
            redirect_url = '/' if redirect_url == oauth2.INITIAL_PAGE else redirect_url
            toolkit.response.location = redirect_url
            helpers.flash_error(error_description)
