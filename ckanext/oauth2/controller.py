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
import constants
import oauth2

import ckan.lib.helpers as helpers
import ckan.lib.base as base

from ckan.common import session
from ckanext.oauth2.plugin import toolkit


log = logging.getLogger(__name__)


class OAuth2Controller(base.BaseController):

    def __init__(self):
        self.oauth2helper = oauth2.OAuth2Helper()

    def callback(self):
        try:
            token = self.oauth2helper.get_token()
            user_name = self.oauth2helper.identify(token)
            self.oauth2helper.remember(user_name)
            self.oauth2helper.update_token(user_name, token)
            self.oauth2helper.redirect_from_callback()
        except Exception as e:

            session.save()

            # If the callback is called with an error, we must show the message
            error_description = toolkit.request.GET.get('error_description')
            if not error_description:
                if e.message:
                    error_description = e.message
                elif hasattr(e, 'description') and e.description:
                    error_description = e.description
                elif hasattr(e, 'error') and e.error:
                    error_description = e.error
                else:
                    error_description = type(e).__name__

            toolkit.response.status_int = 302
            redirect_url = oauth2.get_came_from(toolkit.request.params.get('state'))
            redirect_url = '/' if redirect_url == constants.INITIAL_PAGE else redirect_url
            toolkit.response.location = redirect_url
            helpers.flash_error(error_description)
