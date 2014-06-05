import unittest
import os
import time

from nose_parameterized import parameterized
from selenium import webdriver
from subprocess import Popen, PIPE


class BasicLoginDifferentReferer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env['DEBUG'] = 'True'
        cls._process = Popen(['paster', 'serve', 'test-fiware.ini'], stdout=PIPE, stderr=PIPE, env=env)

    @classmethod
    def tearDownClass(cls):
        cls._process.terminate()

    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(5)
        self.driver.set_window_size(1024, 768)
        self.base_url = "http://localhost:5000/"
        self.verificationErrors = []
        self.accept_next_alert = True

    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

    def test_basic_login(self):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text("Log in").click()
        driver.find_element_by_id("user_email").clear()
        driver.find_element_by_id("user_email").send_keys("filab2@mailinator.com")
        driver.find_element_by_id("user_password").clear()
        driver.find_element_by_id("user_password").send_keys("filab1234")
        driver.find_element_by_name("commit").click()
        self.assertEqual("filab2 Example User", driver.find_element_by_link_text("filab2 Example User").text)
        self.assertEqual(self.base_url, driver.current_url)
        driver.find_element_by_link_text("About").click()
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)
        self.assertEqual(self.base_url + "about", driver.current_url)
        driver.find_element_by_css_selector("a[title=\"Edit settings\"]").click()
        time.sleep(3)   # Wait the OAuth2 Server to return the page
        assert driver.current_url.startswith("https://account.lab.fi-ware.org/settings")

    def test_basic_login_different_referer(self):
        driver = self.driver
        driver.get(self.base_url + "about")
        driver.find_element_by_link_text("Log in").click()
        driver.find_element_by_id("user_email").clear()
        driver.find_element_by_id("user_email").send_keys("filab2@mailinator.com")
        driver.find_element_by_id("user_password").clear()
        driver.find_element_by_id("user_password").send_keys("filab1234")
        driver.find_element_by_name("commit").click()
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)
        self.assertEqual(self.base_url + "about", driver.current_url)
        driver.find_element_by_link_text("Datasets").click()
        self.assertEqual("filab2 Example User", driver.find_element_by_css_selector("span.username").text)
        self.assertEqual(self.base_url + "dataset", driver.current_url)

    def test_user_unauthorized(self):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text("Log in").click()
        driver.find_element_by_id("user_email").clear()
        driver.find_element_by_id("user_email").send_keys("filab3@mailinator.com")
        driver.find_element_by_id("user_password").clear()
        driver.find_element_by_id("user_password").send_keys("filab1234")
        driver.find_element_by_name("commit").click()
        driver.find_element_by_name("cancel").click()
        assert driver.find_element_by_xpath("//div/div/div/div").text.startswith("The end-user or authorization server denied the request.")

    @parameterized.expand([
        ("user/register", "https://account.lab.fi-ware.org/users/sign_up"),
        ("user/reset", "https://account.lab.fi-ware.org/users/password/new")
    ])
    def test_register(self, action, expected_url):
        driver = self.driver
        driver.get(self.base_url + action)
        time.sleep(3)   # Wait the OAuth2 Server to return the page
        self.assertEqual(expected_url, driver.current_url)

if __name__ == "__main__":
    unittest.main()
