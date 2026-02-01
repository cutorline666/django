from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MySeleniumTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        cls.selenium = Chrome(options=opts)
        cls.selenium.implicitly_wait(5)

        # Superusuari per als tests
        user = User.objects.create_user("isard", "isard@isardvdi.com", "pirineus")
        user.is_superuser = True
        user.is_staff = True
        user.save()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_admin_login_and_logout_button_exists(self):
        self.selenium.get(f"{self.live_server_url}/admin/")

        self.selenium.find_element(By.NAME, "username").send_keys("isard")
        self.selenium.find_element(By.NAME, "password").send_keys("pirineus")
        self.selenium.find_element(By.XPATH, "//input[@type='submit']").click()

        # En Django 5.x el logout es un FORM (POST), no un <a>
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.ID, "logout-form"))
        )
        self.selenium.find_element(By.CSS_SELECTOR, "#logout-form button[type='submit']")

    def test_element_should_not_exist_example(self):
        self.selenium.get(f"{self.live_server_url}/admin/")

        try:
            self.selenium.find_element(By.XPATH, "//a[text()='THIS SHOULD NOT EXIST']")
            assert False, "Trobat element que NO hi ha de ser"
        except NoSuchElementException:
            pass
