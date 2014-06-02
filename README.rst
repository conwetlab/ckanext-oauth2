OAuth2 CKAN extension
=====================

The OAuth2 extension allows site visitors to login through an OAuth2 server.

NOTE: This extension requires ckan version 1.7 or higher.


Activating and Installing
-------------------------

To install the plugin, **enter your virtualenv**, download the source and install it:

.. code-block:: bash

    $ git clone https://github.com/conwetlab/ckanext-oauth2
    $ python setup.py develop

Add the following to your CKAN `.ini` file:

.. code-block:: ini

    ckan.plugins = oauth2 <other-plugins>

    ## OAuth2 configuration
    ckan.oauth2.logout_url = /user/logged_out/a
    ckan.oauth2.register_url = https://YOUR_OAUTH_SERVICE/users/sign_up
    ckan.oauth2.reset_url = https://YOUR_OAUTH_SERVICE/users/password/new
    ckan.oauth2.edit_url = https://YOUR_OAUTH_SERVICE/settings


Update your `who.ini` to make use of OAuth2. You must set an Authentication plugin. In this example we use `auth_tkt`:

.. code-block:: ini

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
