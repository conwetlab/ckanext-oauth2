import unittest
import ckanext.oauth2.plugin as plugin

from mock import MagicMock, ANY
from nose_parameterized import parameterized


class PluginTest(unittest.TestCase):

    def setUp(self):
        self._plugin = plugin.OAuth2Plugin()

        # Save functions and mock them
        self._config = plugin.config
        plugin.config = MagicMock()

        self._toolkit = plugin.toolkit
        plugin.toolkit = MagicMock()

        self._session = plugin.session
        plugin.session = MagicMock()

    def tearDown(self):
        # Unmock functions
        plugin.config = self._config
        plugin.toolkit = self._toolkit
        plugin.session = self._session

    def _set_identity(self, identity):
        if identity:
            plugin.toolkit.request.environ = {}
            plugin.toolkit.request.environ['repoze.who.identity'] = {}
            plugin.toolkit.request.environ['repoze.who.identity']['repoze.who.userid'] = identity
        else:
            plugin.toolkit.request.environ = {}

    @parameterized.expand([
        (),
        ('a'),
        (None, 'a',),
        (None, None, 'a'),
        ('a', 'b', 'c')
    ])
    def test_before_map(self, register_url=None, reset_url=None, edit_url=None):

        # Setup the config dictionary
        plugin.config = {}

        if register_url:
            plugin.config['ckan.oauth2.register_url'] = register_url

        if reset_url:
            plugin.config['ckan.oauth2.reset_url'] = reset_url

        if edit_url:
            plugin.config['ckan.oauth2.edit_url'] = edit_url

        # In this case we need a own instance of the plugin, so we create it
        self._plugin = plugin.OAuth2Plugin()

        # Create the mapper (mock) and call the function
        mapper = MagicMock()
        self._plugin.before_map(mapper)

        # Check that the mapper has been called correctly
        mapper.connect.assert_called_with('/oauth2/callback',
                                          controller='ckanext.oauth2.controller:OAuth2Controller',
                                          action='callback')

        if register_url:
            mapper.redirect.assert_any_call('/user/register', register_url)

        if reset_url:
            mapper.redirect.assert_any_call('/user/reset', reset_url)

        if edit_url:
            mapper.redirect.assert_any_call('/user/edit/{user}', edit_url)

    def test_auth_functions(self):

        EXPECTED_AUTH_FUNCTIONS = ['user_create', 'user_update', 'user_reset', 'request_reset']

        auth_functions = self._plugin.get_auth_functions()

        for auth_function in auth_functions:
            self.assertIn(auth_function, EXPECTED_AUTH_FUNCTIONS)
            function_result = auth_functions[auth_function]({'user': 'test'}, {})
            self.assertIn('success', function_result)
            self.assertEquals(False, function_result['success'])

    @parameterized.expand([
        (None,),
        ('test')
    ])
    def test_identify(self, identity=None):

        self._set_identity(identity)

        # The identify function must set the user id in this variable
        plugin.toolkit.c.user = None

        # Call the function
        self._plugin.identify()

        self.assertEquals(identity, plugin.toolkit.c.user)
        plugin.session.save.assert_called_once()

    @parameterized.expand([
        (),
        ('test'),
        (None, '/about'),
        ('test', '/about')
    ])
    def test_login(self, user=None, referer=None):

        expected_referer = '/' if referer is None else referer

        # The login function will check this variables
        plugin.toolkit.c.user = user
        plugin.toolkit.request.headers = {}
        if referer:
            plugin.toolkit.request.headers['Referer'] = referer

        # Call the function
        self._plugin.login()

        if not user:
            plugin.toolkit.abort.assert_called_once_with(401)
        else:
            self.assertEquals(0, plugin.toolkit.abort.call_count)
            plugin.toolkit.redirect_to.assert_called_with(bytes(expected_referer))

    @parameterized.expand([
        (),
        ('test'),
        (None, '/about'),
        ('test', '/about')
    ])
    def test_logout(self, identity=None, logout_url=None):

        self._set_identity(identity)
        expected_logout_url = '/user/logged_out' if logout_url is None else logout_url

        plugin.config = {}
        if logout_url:
            plugin.config['ckan.oauth2.logout_url'] = logout_url

        # The plugin needs to be recreated
        self._plugin = plugin.OAuth2Plugin()

        # Generate the plugins
        validPlugin = MagicMock()
        validPlugin.forget = MagicMock(return_value=[('head1', 'val1'), ('head2', 'val2')])
        invalidPlugin = MagicMock()
        del invalidPlugin.forget

        # Put the plugins in the environ that is read by the function
        plugin.toolkit.request.environ['repoze.who.plugins'] = {}
        plugin.toolkit.request.environ['repoze.who.plugins']['pluginA'] = validPlugin
        plugin.toolkit.request.environ['repoze.who.plugins']['pluginB'] = invalidPlugin

        # Call the function
        self._plugin.logout()

        if identity:
            # Chech that the function forget of the plugin is called
            validPlugin.forget(plugin.toolkit.request.environ, identity)

            #Check that all the headers are set in the response
            for head, value in validPlugin.forget.return_value:
                plugin.toolkit.response.headers.add.assert_any_call(head, value)

        plugin.toolkit.redirect_to.assert_called_with(bytes(expected_logout_url), locale=ANY)
