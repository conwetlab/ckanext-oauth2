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

from flask import Blueprint, redirect

import ckan.model as model
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as helpers

from ckanext.oauth2 import constants
from ckanext.oauth2.oauth2 import get_came_from
from ckanext.oauth2.plugin import _get_previous_page


log = logging.getLogger(__name__)

oauth2 = Blueprint('oauth2', __name__)


def get_blueprints():
    return [oauth2]


def _get_oauth2helper():
    """Get OAuth2Helper from the loaded plugin singleton."""
    plugin = plugins.get_plugin('oauth2')
    return plugin.oauth2helper


@oauth2.route('/user/login')
def login():
    log.debug('login')
    came_from_url = _get_previous_page(constants.INITIAL_PAGE)
    return _get_oauth2helper().challenge(came_from_url)


@oauth2.route('/oauth2/callback')
def callback():
    try:
        oauth2helper = _get_oauth2helper()
        token = oauth2helper.get_token()
        user_name, user_obj = oauth2helper.identify(token)
        oauth2helper.log_user_into_ckan(user_obj)
        oauth2helper.update_token(user_name, token)
        response = oauth2helper.redirect_from_callback()
    except Exception as e:
        model.Session.rollback()

        error_description = toolkit.request.args.get('error_description')
        if not error_description:
            if str(e):
                error_description = str(e)
            elif hasattr(e, 'description') and e.description:
                error_description = e.description
            elif hasattr(e, 'error') and e.error:
                error_description = e.error
            else:
                error_description = type(e).__name__

        log.error('login error: %s', error_description)

        redirect_url = get_came_from(toolkit.request.args.get('state'))
        if redirect_url == constants.INITIAL_PAGE:
            redirect_url = '/'
        response = redirect(redirect_url)
        helpers.flash_error(error_description)

    return response
