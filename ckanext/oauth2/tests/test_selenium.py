# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2017 CoNWeT Lab., Universidad Politécnica de Madrid

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

import unittest
import os
import time

from urlparse import urljoin
from nose_parameterized import parameterized
from selenium import webdriver
from subprocess import Popen

IDM_URL = "https://account.lab.fiware.org"
FILAB2_MAIL = "filab2@mailinator.com"
FILAB3_MAIL = "filab3@mailinator.com"
FILAB_PASSWORD = "filab1234"


class IntegrationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env['DEBUG'] = 'True'
        env['OAUTHLIB_INSECURE_TRANSPORT'] = 'True'
        cls._process = Popen(['paster', 'serve', 'test-fiware.ini'], env=env)

        if 'WEB_DRIVER_URL' in os.environ and 'CKAN_SERVER_URL' in os.environ:
            cls.driver = webdriver.Remote(os.environ['WEB_DRIVER_URL'], webdriver.DesiredCapabilities.FIREFOX.copy())
            cls.base_url = os.environ['CKAN_SERVER_URL']
        else:
            cls.driver = webdriver.Firefox()
            cls.base_url = 'http://localhost:5000/'

        cls.driver.implicitly_wait(5)
        cls.driver.set_window_size(1024, 768)

        cls.driver.get(IDM_URL)
        cls._introduce_log_in_parameters()
        cls.driver.get(urljoin(IDM_URL, '/idm/myApplications/361020fd7cf64456890dd98da88e64f3/edit/'))
        cls.driver.find_element_by_id("id_callbackurl").clear()
        cls.driver.find_element_by_id("id_callbackurl").send_keys(urljoin(cls.base_url, '/oauth2/callback'))
        cls.driver.find_element_by_xpath("//button[@type='submit']").click()

    @classmethod
    def tearDownClass(cls):
        cls._process.terminate()
        cls.driver.quit()

    @classmethod
    def _introduce_log_in_parameters(cls, username=FILAB2_MAIL, password=FILAB_PASSWORD):
        driver = cls.driver
        driver.find_element_by_id("id_username").clear()
        driver.find_element_by_id("id_username").send_keys(username)
        driver.find_element_by_id("id_password").clear()
        driver.find_element_by_id("id_password").send_keys(password)
        driver.find_element_by_xpath("//button[@type='submit']").click()

    def delete_cookies(self, domain):
        self.driver.get(domain)
        self.driver.delete_all_cookies()

    def setUp(self):
        self.delete_cookies(IDM_URL)
        self.delete_cookies(self.base_url)
        self.verificationErrors = []
        self.accept_next_alert = True

    def tearDown(self):
        self.assertEqual([], self.verificationErrors)

    def _log_in(self, referer, username=FILAB2_MAIL, password=FILAB_PASSWORD, authorize=True):
        driver = self.driver
        driver.get(referer)
        driver.find_element_by_link_text("Log in").click()
        self._introduce_log_in_parameters(username, password)

        if driver.current_url.startswith(IDM_URL) and authorize:
            driver.find_element_by_xpath("//button[@type='submit']").click()

    def test_basic_login(self):
        driver = self.driver
        self._log_in(self.base_url)
        self.assertEqual("filab2 Example User", driver.find_element_by_link_text("filab2 Example User").text)
        self.assertEqual(self.base_url + 'dashboard', driver.current_url)
        driver.find_element_by_link_text("About").click()
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)
        self.assertEqual(self.base_url + "about", driver.current_url)
        driver.find_element_by_css_selector("a[title=\"Edit settings\"]").click()
        time.sleep(3)   # Wait the OAuth2 Server to return the page
        assert driver.current_url.startswith(IDM_URL + "/settings")

    def test_basic_login_different_referer(self):
        driver = self.driver
        self._log_in(self.base_url + "about")
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)
        self.assertEqual(self.base_url + "about", driver.current_url)
        driver.find_element_by_link_text("Datasets").click()
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)
        self.assertEqual(self.base_url + "dataset", driver.current_url)

    def test_user_access_unauthorized_page(self):
        driver = self.driver
        self._log_in(self.base_url)
        time.sleep(3)   # Wait until the log in proccess is completed
        driver.get(self.base_url + "ckan-admin")

        # Check that the user has been redirected to the main page
        self.assertEquals(self.base_url, driver.current_url)
        # Check that an error message is shown
        assert driver.find_element_by_xpath("//div/div/div/div").text.startswith("Need to be system administrator to administer")

    def test_register_btn(self):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text("Register").click()
        self.assertEqual(IDM_URL + "/sign_up/", driver.current_url)

    @parameterized.expand([
        ("user/register", IDM_URL + "/sign_up/"),
        ("user/reset", IDM_URL + "/password/request/")
    ])
    def test_register(self, action, expected_url):
        driver = self.driver
        driver.get(self.base_url + action)
        time.sleep(3)   # Wait the OAuth2 Server to return the page
        self.assertEqual(expected_url, driver.current_url)


if __name__ == "__main__":
    unittest.main()
