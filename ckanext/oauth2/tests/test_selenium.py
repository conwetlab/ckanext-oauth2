from selenium import webdriver
from subprocess import Popen, PIPE
import unittest


class BasicLoginDifferentReferer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._process = Popen(['paster', 'serve', 'test-fiware.ini'], stdout=PIPE)

    @classmethod
    def tearDownClass(cls):
        cls._process.terminate()

    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(5)
        self.driver.maximize_window()
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

if __name__ == "__main__":
    unittest.main()
