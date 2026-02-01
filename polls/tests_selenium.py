import os
import uuid
from unittest import SkipTest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class AdminGroupsSeleniumTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        opts = Options()
        if os.environ.get("HEADLESS", "true").lower() in ("1", "true", "yes"):
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1400,1000")

        try:
            cls.selenium = Chrome(options=opts)
            cls.selenium.implicitly_wait(0)
        except Exception as e:
            raise SkipTest(f"Selenium/Chrome no disponible: {e}")

    @classmethod
    def tearDownClass(cls):
        try:
            if hasattr(cls, "selenium"):
                cls.selenium.quit()
        finally:
            super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )

    def wait(self, timeout=20):
        return WebDriverWait(self.selenium, timeout)

    def login_admin(self):
        self.selenium.get(f"{self.live_server_url}/admin/login/")
        self.wait().until(EC.presence_of_element_located((By.ID, "id_username")))
        self.selenium.find_element(By.ID, "id_username").clear()
        self.selenium.find_element(By.ID, "id_username").send_keys("admin")
        self.selenium.find_element(By.ID, "id_password").send_keys("adminpass123")
        self.selenium.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        # Ya dentro del admin
        self.wait().until(EC.presence_of_element_located((By.ID, "content")))
        self.assertNotIn("/admin/login/", self.selenium.current_url)

    def test_create_group_and_appears_in_user_form(self):
        self.login_admin()

        group_name = f"EAC2_Group_{uuid.uuid4().hex[:8]}"

        # 1) Crear Group en admin
        self.selenium.get(f"{self.live_server_url}/admin/auth/group/add/")
        self.wait().until(EC.presence_of_element_located((By.ID, "id_name")))
        self.selenium.find_element(By.ID, "id_name").send_keys(group_name)
        self.selenium.find_element(By.NAME, "_save").click()

        # Espera a salir del /add/
        self.wait().until(lambda d: "/admin/auth/group/" in d.current_url and "/add/" not in d.current_url)
        self.assertTrue(Group.objects.filter(name=group_name).exists(), "El grupo no se guardó en la BD")

        # 2) Verificar que aparece en la lista de groups (/admin/auth/group/)
        self.selenium.get(f"{self.live_server_url}/admin/auth/group/")
        self.wait().until(EC.presence_of_element_located((By.ID, "changelist")))

        # Espera explícita a que aparezca el enlace del grupo
        self.wait().until(EC.presence_of_element_located((By.LINK_TEXT, group_name)))

        # 3) Crear un usuario (paso 1)
        self.selenium.get(f"{self.live_server_url}/admin/auth/user/add/")
        self.wait().until(EC.presence_of_element_located((By.ID, "id_username")))

        new_username = f"user_{uuid.uuid4().hex[:6]}"
        new_password = "StrongPassw0rd!!"

        self.selenium.find_element(By.ID, "id_username").send_keys(new_username)
        self.selenium.find_element(By.ID, "id_password1").send_keys(new_password)
        self.selenium.find_element(By.ID, "id_password2").send_keys(new_password)
        self.selenium.find_element(By.NAME, "_save").click()

        # 4) Ya en el change form del usuario (paso 2)
        self.wait().until(lambda d: "/admin/auth/user/" in d.current_url and "/change/" in d.current_url)
        self.assertNotIn("/admin/login/", self.selenium.current_url)

        # En el change form debe existir selector de grupos (filtered o select simple)
        def group_option_present(d):
            # FilteredSelectMultiple típico: id_groups_from
            if d.find_elements(By.ID, "id_groups_from"):
                return len(d.find_elements(
                    By.XPATH,
                    f"//select[@id='id_groups_from']/option[normalize-space()='{group_name}']"
                )) > 0

            # Select múltiple simple: id_groups
            if d.find_elements(By.ID, "id_groups"):
                return len(d.find_elements(
                    By.XPATH,
                    f"//select[@id='id_groups']/option[normalize-space()='{group_name}']"
                )) > 0

            return False

        self.wait().until(group_option_present)
