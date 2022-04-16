import logging
from flask import Blueprint, jsonify, make_response
import logging
from ckanext.oauth2 import constants
from ckan.common import session
import ckan.lib.helpers as helpers
import ckan.plugins.toolkit as toolkit
import urllib.parse
from ckanext.oauth2.oauth2 import OAuth2Helper

log = logging.getLogger(__name__)

oauth2 = Blueprint("oauth2", __name__)

oauth2helper = OAuth2Helper()

def _get_previous_page(default_page):
    if 'came_from' not in toolkit.request.params:
        came_from_url = toolkit.request.headers.get('Referer', default_page)
    else:
        came_from_url = toolkit.request.params.get('came_from', default_page)

    came_from_url_parsed = urllib.parse.urlparse(came_from_url)

    # Avoid redirecting users to external hosts
    if came_from_url_parsed.netloc != '' and came_from_url_parsed.netloc != toolkit.request.host:
        came_from_url = default_page

    # When a user is being logged and REFERER == HOME or LOGOUT_PAGE
    # he/she must be redirected to the dashboard
    pages = ['/', '/user/logged_out_redirect']
    if came_from_url_parsed.path in pages:
        came_from_url = default_page

    return came_from_url

@oauth2.route('/user/login')
def login():
    log.debug('login')

    # Log in attemps are fired when the user is not logged in and they click
    # on the log in button

    # Get the page where the user was when the loggin attemp was fired
    # When the user is not logged in, he/she should be redirected to the dashboard when
    # the system cannot get the previous page
    came_from_url = _get_previous_page(constants.INITIAL_PAGE)
    return oauth2helper.challenge(came_from_url)

@oauth2.route('/oauth2/callback')
def callback():

    try:
        token = oauth2helper.get_token()

        user_name = oauth2helper.identify(token)
        response = oauth2helper.remember(user_name)
        log.debug(f'usr:{user_name}')

        oauth2helper.update_token(user_name, token)
        response = oauth2helper.redirect_from_callback(response)
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
        response = jsonify()
        response.status_code = 302
        redirect_url = oauth2.get_came_from(toolkit.request.params.get('state'))
        redirect_url = '/' if redirect_url == constants.INITIAL_PAGE else redirect_url
        response.location = redirect_url
        helpers.flash_error(error_description)
    return response

def get_blueprints():
    return [oauth2]
