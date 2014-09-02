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

import cgi
import logging

import ckan.lib.helpers as helpers
import ckan.lib.base as base
import ckanext.oauth2.repozewho as oauth2_repozewho

from ckan.common import request, response

log = logging.getLogger(__name__)


class OAuth2Controller(base.BaseController):

    def callback(self):
        '''
        If the callback is called properly, this function won't be executed.
        This function is only executed when an error arises login the user in
        the OAuth2 Server (i.e.: a user doesn't allow the application to access
        their data, the application is not running over HTTPs,...)
        '''
        log.debug('Callback Controller')
        # Move to the came_from page coded in the state of the OAuth request
        response.status_int = 302   # FOUND
        redirect_url = oauth2_repozewho.get_came_from(request.params.get('state'))
        redirect_url = '/' if redirect_url == oauth2_repozewho.INITIAL_PAGE else redirect_url
        response.location = redirect_url
        helpers.flash_error(cgi.escape(request.GET.get('error_description',
                            'It was impossible to log in you using the OAuth2 Service')))
