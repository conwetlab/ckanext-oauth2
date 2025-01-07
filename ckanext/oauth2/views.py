import logging
from flask import Blueprint, jsonify, make_response, redirect, abort
import logging
from ckanext.oauth2 import constants
from ckan.common import session
import ckan.lib.helpers as helpers
import ckan.plugins.toolkit as toolkit
import urllib.parse
from ckanext.oauth2.oauth2 import OAuth2Helper, get_came_from

log = logging.getLogger(__name__)

# service_proxy = Blueprint("service_proxy", __name__)
oauth2 = Blueprint("oauth2", __name__)
oauth2helper = OAuth2Helper()

def get_plugin_class():
    from ckanext.oauth2.plugin import OAuth2Plugin
    oauth2plugin = OAuth2Plugin()
    return oauth2plugin

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
        # log.debug(f'token:{token}')
        user_name,user_obj = oauth2helper.identify(token)
        oauth2helper.log_user_into_ckan(user_obj)
        oauth2helper.update_token(user_name, token)
        response = oauth2helper.redirect_from_callback()
    except Exception as e:

        session.save()

        # If the callback is called with an error, we must show the message
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
        log.error(f'login error: {error_description}')         
        redirect_url = get_came_from(toolkit.request.params.get('state'))
        redirect_url = '/' if redirect_url == constants.INITIAL_PAGE else redirect_url
        response = redirect(redirect_url)
        helpers.flash_error(error_description)

    return response

@oauth2.route('/user/edit/<user>')
def edit(user):
    u''' This function will redirect the profile setting with
        oauth2.edit_url mentioned in ckan.ini.
    '''
    log.debug("edit profile")
    #get oauth2plugin
    oauth2plugin = get_plugin_class()
    if oauth2plugin.edit_url:
        redirect_url = toolkit.url_for(oauth2plugin.edit_url,  _external=True)
        return redirect(redirect_url)
    else :
       abort(403, "You don't have permission to edit this profile.")

@oauth2.route('/user/register')
def register():
    u''' This function will redirect the register url with
        oauth2.register_url mentioned in ckan.ini.
    '''
    log.debug("regsiter user")
    #get oauth2plugin
    oauth2plugin = get_plugin_class()
    if oauth2plugin.register_url:
        redirect_url = toolkit.url_for(oauth2plugin.register_url,  _external=True)
        return redirect(redirect_url)
    else :
       abort(403, "You are not authorized to register as a user.")

@oauth2.route('/user/reset')
def reset():
    u''' This function will redirect the reset url with
        oauth2.reset_url mentioned in ckan.ini.
    '''
    log.debug("reset user")
    #get oauth2plugin
    oauth2plugin = get_plugin_class()
    if oauth2plugin.reset_url:
        redirect_url = toolkit.url_for(oauth2plugin.reset_url,  _external=True)
        return redirect(redirect_url)
    else :
       abort(403, "You are not authorized to request a password reset.")

def get_blueprints():
    return [oauth2]
