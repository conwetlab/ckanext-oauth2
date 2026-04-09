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

from flask import Blueprint

from ckan.plugins import toolkit
from ckan.common import session
import ckan.lib.helpers as helpers

from ckanext.oauth2 import constants
from ckanext.oauth2.oauth2 import OAuth2Helper, get_came_from
from ckanext.oauth2.plugin import _get_previous_page


log = logging.getLogger(__name__)

oauth2_blueprint = Blueprint('oauth2', __name__)


def login():
    log.debug('login')

    # Get the page where the user was when the login attempt was fired
    came_from_url = _get_previous_page(constants.INITIAL_PAGE)

    oauth2helper = OAuth2Helper()
    return oauth2helper.challenge(came_from_url)


def callback():
    try:
        oauth2helper = OAuth2Helper()
        token = oauth2helper.get_token()
        user_name = oauth2helper.identify(token)
        oauth2helper.remember(user_name)
        oauth2helper.update_token(user_name, token)
        return oauth2helper.redirect_from_callback()
    except Exception as e:
        session.save()

        # If the callback is called with an error, we must show the message
        error_description = toolkit.request.args.get('error_description')
        if not error_description:
            error_description = str(e) if str(e) else type(e).__name__

        state = toolkit.request.args.get('state', '')
        redirect_url = get_came_from(state) if state else '/'
        if redirect_url == constants.INITIAL_PAGE:
            redirect_url = '/'
        helpers.flash_error(error_description)
        return toolkit.redirect_to(redirect_url)


oauth2_blueprint.add_url_rule('/user/login', view_func=login)
oauth2_blueprint.add_url_rule('/oauth2/callback', view_func=callback)
