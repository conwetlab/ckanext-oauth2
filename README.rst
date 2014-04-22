OAuth2 CKAN extension
=====================

The OAuth2 extension allows site visitors to login through an OAuth2 server.

NOTE: This extension requires ckan version 1.7 or higher.


Activating and Installing
-------------------------

To install the plugin, enter your virtualenv and load the source:

.. code-block:: bash

    $ pip install ckanext-oauth2

Add the following to your CKAN .ini file:

.. code-block:: ini

    ckan.plugins = oauth2 <other-plugins>


Update your who.ini to make use of OAuth2:

.. code-block:: ini

    [plugin:oauth2]
    use = ckanext.oauth2.repozewho:make_plugin
    authorization_endpoint = https://auth.domain.com/oauth2/authorize/
    token_endpoint = https://auth.domain.com/oauth2/token/
    client_id = client-id
    client_secret = client-secret
    scope = profile another.scope
    rememberer_name = fake

    [plugin:fake]
    use = ckanext.oauth2.tests.utils:FakeRememberer

    [identifiers]
    plugins = oauth2 fake

    [authenticators]
    plugins = oauth2

    [challengers]
    plugins = oauth2

    [general]
    challenge_decider = repoze.who.classifiers:default_challenge_decider
    request_classifier = repoze.who.classifiers:default_request_classifier

