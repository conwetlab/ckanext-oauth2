# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2017 CoNWeT Lab., Universidad Politécnica de Madrid
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

import unittest
import os
from subprocess import Popen
import time
from urlparse import urljoin

from parameterized import parameterized
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

IDM_URL = "https://account.lab.fiware.org"
FILAB2_MAIL = "filab2@mailinator.com"
FILAB3_MAIL = "filab3@mailinator.com"
FILAB_PASSWORD = "filab1234"
PASS_INTEGRATION_TESTS = os.environ.get("INTEGRATION_TEST", "").strip().lower() in ('1', 'true', 'on')

@unittest.skipUnless(PASS_INTEGRATION_TESTS, "set INTEGRATION_TEST environment variable (e.g. INTEGRATION_TEST=true) for running the integration tests")
class IntegrationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # nose calls this method also if they are going to be skiped
        if not PASS_INTEGRATION_TESTS:
            return

        env = os.environ.copy()
        env['DEBUG'] = 'True'
        env['OAUTHLIB_INSECURE_TRANSPORT'] = 'True'
        cls._process = Popen(['paster', 'serve', 'test-fiware.ini'], env=env)

        cls.driver = webdriver.Firefox()
        cls.base_url = 'http://localhost:5000/'
        cls.driver.set_window_size(1024, 768)

        cls.driver.get(IDM_URL)
        cls._introduce_log_in_parameters()
        cls.driver.get(urljoin(IDM_URL, '/idm/myApplications/361020fd7cf64456890dd98da88e64f3/edit/'))
        id_callbackurl = WebDriverWait(cls.driver, 10).until(EC.presence_of_element_located((By.ID, "id_callbackurl")))
        id_callbackurl.clear()
        id_callbackurl.send_keys(urljoin(cls.base_url, '/oauth2/callback'))
        cls.driver.find_element_by_xpath("//button[@type='submit']").click()

    @classmethod
    def tearDownClass(cls):
        # nose calls this method also if they are going to be skiped
        if not PASS_INTEGRATION_TESTS:
            return

        cls._process.terminate()
        cls.driver.quit()

    @classmethod
    def _introduce_log_in_parameters(cls, username=FILAB2_MAIL, password=FILAB_PASSWORD):
        driver = cls.driver
        id_username = WebDriverWait(cls.driver, 10).until(EC.presence_of_element_located((By.ID, "id_username")))
        id_username.clear()
        id_username.send_keys(username)
        driver.find_element_by_id("id_password").clear()
        driver.find_element_by_id("id_password").send_keys(password)
        driver.find_element_by_xpath("//button[@type='submit']").click()
        WebDriverWait(driver, 30).until(EC.staleness_of(id_username))

    def delete_cookies(self, domain):
        self.driver.get(domain)
        self.driver.delete_all_cookies()

    def setUp(self):
        self.delete_cookies(self.base_url)
        self.delete_cookies(IDM_URL)
        self.verificationErrors = []
        self.accept_next_alert = True

    def tearDown(self):
        self.assertEqual([], self.verificationErrors)

    def _log_in(self, referer, username=FILAB2_MAIL, password=FILAB_PASSWORD, authorize=True):
        driver = self.driver
        driver.get(referer)
        WebDriverWait(driver, 30).until(lambda driver: driver.current_url == referer)

        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.LINK_TEXT, "Log in"))).click()
        self._introduce_log_in_parameters(username, password)

        if driver.current_url.startswith(IDM_URL) and authorize:
            WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()

    def test_basic_login(self):
        driver = self.driver
        self._log_in(self.base_url)
        WebDriverWait(driver, 20).until(lambda driver: (self.base_url + 'dashboard') == driver.current_url)
        self.assertEqual("filab2 Example User", driver.find_element_by_link_text("filab2 Example User").text)
        driver.find_element_by_link_text("About").click()
        WebDriverWait(driver, 20).until(lambda driver: (self.base_url + 'about') == driver.current_url)
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)
        driver.find_element_by_css_selector("a[title=\"Edit settings\"]").click()
        time.sleep(3)   # Wait the OAuth2 Server to return the page
        assert driver.current_url.startswith(IDM_URL + "/settings")

    def test_basic_login_different_referer(self):
        driver = self.driver
        self._log_in(self.base_url + "about")
        WebDriverWait(driver, 20).until(lambda driver: (self.base_url + 'about') == driver.current_url)
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)
        driver.find_element_by_link_text("Datasets").click()
        WebDriverWait(driver, 20).until(lambda driver: (self.base_url + 'dataset') == driver.current_url)
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)

    def test_user_access_unauthorized_page(self):
        driver = self.driver
        self._log_in(self.base_url)
        driver.get(self.base_url + "ckan-admin")

        # Check that the user has been redirected to the main page
        WebDriverWait(driver, 10).until(lambda driver: driver.current_url == self.base_url)
        # Check that an error message is shown
        assert driver.find_element_by_xpath("//div/div/div/div").text.startswith("Need to be system administrator to administer")

    def test_register_btn(self):
        driver = self.driver
        driver.get(self.base_url)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "Register"))).click()
        WebDriverWait(driver, 10).until(lambda driver: driver.current_url == (IDM_URL + "/sign_up/"))

    @parameterized.expand([
        ("user/register", IDM_URL + "/sign_up/"),
        ("user/reset", IDM_URL + "/password/request/")
    ])
    def test_register(self, action, expected_url):
        driver = self.driver
        driver.get(self.base_url + action)
        WebDriverWait(driver, 10).until(lambda driver: driver.current_url == expected_url)


if __name__ == "__main__":
    unittest.main()
