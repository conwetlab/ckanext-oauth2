To install the plugin, **enter your virtualenv**, download the source and install it:

```
$ git clone https://github.com/conwetlab/ckanext-oauth2
$ python setup.py develop
```

Add the following to your CKAN `.ini` file:

```
ckan.plugins = oauth2 <other-plugins>

## OAuth2 configuration
ckan.oauth2.logout_url = /user/logged_out
ckan.oauth2.register_url = https://YOUR_OAUTH_SERVICE/users/sign_up
ckan.oauth2.reset_url = https://YOUR_OAUTH_SERVICE/users/password/new
ckan.oauth2.edit_url = https://YOUR_OAUTH_SERVICE/settings
ckan.oauth2.authorization_endpoint = https://YOUR_OAUTH_SERVICE/authorize
ckan.oauth2.token_endpoint = https://YOUR_OAUTH_SERVICE/token
ckan.oauth2.profile_api_url = https://YOUR_OAUTH_SERVICE/user
ckan.oauth2.client_id = YOUR_CLIENT_ID
ckan.oauth2.client_secret = YOUR_CLIENT_SECRET
ckan.oauth2.scope = profile other.scope
ckan.oauth2.rememberer_name = auth_tkt
ckan.oauth2.profile_api_user_field = JSON_FIELD_TO_FIND_THE_USER_IDENTIFIER
ckan.oauth2.profile_api_fullname_field = JSON_FIELD_TO_FIND_THE_USER_FULLNAME
ckan.oauth2.profile_api_mail_field = JSON_FIELD_TO_FIND_THE_USER_MAIL
ckan.oauth2.authorization_header = OAUTH2_HEADER
```

**Additional notes**:
* This extension only works when your CKAN instance is working over HTTPS, since OAuth 2.0 depends on it. You can follow the [Starting CKAN over HTTPs tutorial](https://github.com/conwetlab/ckanext-oauth2/wiki/Starting-CKAN-over-HTTPs) to learn how to do that. 
* The callback URL that you should set on your OAuth 2.0 is: `https://YOUR_CKAN_INSTANCE/oauth2/callback`, replacing `YOUR_CKAN_INSTANCE` by the machine and port where your CKAN instance is running. 