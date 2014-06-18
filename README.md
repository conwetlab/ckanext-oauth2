OAuth2 CKAN extension  [![Build Status](http://hercules.ls.fi.upm.es/jenkins/buildStatus/icon?job=ckan_oauth2)](http://hercules.ls.fi.upm.es/jenkins/job/ckan_oauth2/)
=====================

The OAuth2 extension allows site visitors to login through an OAuth2 server.

NOTE: This extension requires ckan version 1.7 or higher.


Activating and Installing
-------------------------

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
```

Update your `who.ini` to make use of OAuth2. You must set an Authentication plugin. In this example we use `auth_tkt`:

```
[plugin:oauth2]
use = ckanext.oauth2.repozewho:make_plugin
authorization_endpoint = https://YOUR_OAUTH_SERVICE/authorize
token_endpoint = https://YOUR_OAUTH_SERVICE/token
profile_api_url = https://YOUR_OAUTH_SERVICE/user
client_id = YOUR_CLIENT_ID
client_secret = YOUR_CLIENT_SECRET
scope = profile other.scope
rememberer_name = auth_tkt
profile_api_user_field = JSON_FIELD_TO_FIND_THE_USER_IDENTIFIER
profile_api_fullname_field = JSON_FIELD_TO_FIND_THE_USER_FULLNAME
profile_api_mail_field = JSON_FIELD_TO_FIND_THE_USER_MAIL
[plugin:auth_tkt]
use = repoze.who.plugins.auth_tkt:make_plugin
secret = somesecret

[identifiers]
plugins = oauth2 auth_tkt

[authenticators]
plugins = oauth2

[challengers]
plugins = oauth2

[general]
challenge_decider = repoze.who.classifiers:default_challenge_decider
request_classifier = repoze.who.classifiers:default_request_classifier
```

**Additional notes**:
* This extension only works when your CKAN instance is working over HTTPS, since OAuth 2.0 depends on it. 
* The callback URL that you should set on your OAuth 2.0 is: `https://YOUR_CKAN_INSTANCE/oauth2/callback`, replacing `YOUR_CKAN_INSTANCE` by the machine and port where your CKAN instance is running. 


How it works?
-------------
1. If the user tries to perform a log in and it's not currently logged in, a 401 exception is raised by the `login` function of the `plugin.py` file. Under this circumstances, is the function `challenge` called. This function will only redirect the user to the OAuth2 Server log in page when a login attempt is performed. The `challenge` function ignores the 401 exceptions raised because the user doesn't have grants to perform an operation.
2. Once that the user completes the log in, he or she is redirected to the page `/oauth2/callback` of the CKAN instance. In this case, the `identify` function of the `repozewho.py` file captures the request and tries to get the OAuth2 token. If the operation can be performed without exceptions, the `authenticate` function will be executed with the value returned by the `identify` function. Otherwise, a message error will be shown.
3. The `authenticate` function should return the user identifier. To do so, the function asks for the basic user information to the OAuth2 server with the token returned by the `identify` function. Once that the user identifier is got, the user model is asked for that user. If the user does not exist, it's created. Otherwise, the user is updated. Finally the function returns the user identifier.
4. Then, the `remember` function is called to set the cookies that allow the system to identify the user without performing another login attempt. 
5. The `identify` function of the `plugin.py` file read the property `repoze.who.identity` from the request environ. This variable is automatically set using the cookies stored by the authenticate process explained above. If the user is logged, this variable contains the user identifier. In this case, the variable `toolkit.c.user` is set to the user identifier. Otherwise, the variable is set to None. 



