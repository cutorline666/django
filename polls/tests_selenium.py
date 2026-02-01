import uuid

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class AdminGroupsSeleniumTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-gpu")

        cls.selenium = Chrome(options=opts)
        cls.selenium.implicitly_wait(5)

        u = User.objects.create_user("isard", "isard@isardvdi.com", "pirineus")
        u.is_superuser = True
        u.is_staff = True
        u.save()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.selenium.quit()
        finally:
            super().tearDownClass()

    def wait(self, secs=10):
        return WebDriverWait(self.selenium, secs)

    def login_admin(self):
        self.selenium.get(f"{self.live_server_url}/admin/login/")
        self.wait().until(EC.presence_of_element_located((By.NAME, "username")))

        self.selenium.find_element(By.NAME, "username").send_keys("isard")
        self.selenium.find_element(By.NAME, "password").send_keys("pirineus")
        self.selenium.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        # Django 5.x: logout es un FORM con id logout-form
        self.wait().until(EC.presence_of_element_located((By.ID, "logout-form")))

    def open_all_details(self):
        # En Django 5.x algunos fieldsets vienen dentro de <details> colapsados
        for d in self.selenium.find_elements(By.CSS_SELECTOR, "details"):
            is_open = d.get_attribute("open")
            if not is_open:
                try:
                    d.find_element(By.CSS_SELECTOR, "summary").click()
                except Exception:
                    pass

    def test_create_group_and_appears_in_user_form(self):
        self.login_admin()

        group_name = f"EAC2_Group_{uuid.uuid4().hex[:8]}"

        # 1) Crear Group en admin
        self.selenium.get(f"{self.live_server_url}/admin/auth/group/add/")
        self.wait().until(EC.presence_of_element_located((By.ID, "id_name")))
        self.selenium.find_element(By.ID, "id_name").send_keys(group_name)
        self.selenium.find_element(By.NAME, "_save").click()

        # 4) Verificar que el grupo aparece entre los asignables al usuario
        self.wait().until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert "/admin/login/" not in self.selenium.current_url, f"Redirigido a login: {self.selenium.current_url}"

        # abrir Permissions si esta colapsado (Django admin puede colapsar fieldsets)
        try:
            self.selenium.find_element(By.XPATH, "//summary[contains(.,\"Permissions\")]").click()
        except Exception:
            pass

        # espera a que exista el selector de grupos (segun layout de Django)
        self.wait().until(lambda d: d.find_elements(By.ID, "id_groups_from") or d.find_elements(By.ID, "id_groups"))

        if self.selenium.find_elements(By.ID, "id_groups_from"):
            self.selenium.find_element(By.XPATH, f"//select[@id=id_groups_from]/option[normalize-space()={group_name}]")
        else:
            self.selenium.find_element(By.XPATH, f"//select[@id=id_groups]/option[normalize-space()={group_name}]")

        self.wait().until(EC.presence_of_element_located((By.ID, "content")))

        # 2) Verificar que aparece en la lista de groups
        self.selenium.get(f"{self.live_server_url}/admin/auth/group/")

        # espera a que cargue la página
        self.wait().until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # si te ha mandado al login, aquí lo verás claro
        assert "/admin/login/" not in self.selenium.current_url, f"Redirigido a login: {self.selenium.current_url}"

        # en la vista changelist del admin siempre existe este contenedor
        self.wait().until(EC.presence_of_element_located((By.ID, "changelist")))

        # y el grupo debe aparecer como enlace
        self.selenium.find_element(By.XPATH, f"//a[normalize-space()='{group_name}']")

# 3) Crear un usuario (paso 1)
        self.selenium.get(f"{self.live_server_url}/admin/auth/user/add/")
        self.wait().until(EC.presence_of_element_located((By.ID, "id_username")))

        new_username = f"user_{uuid.uuid4().hex[:6]}"
        new_password = "StrongPassw0rd!!"

        self.selenium.find_element(By.ID, "id_username").send_keys(new_username)
        self.selenium.find_element(By.ID, "id_password1").send_keys(new_password)
        self.selenium.find_element(By.ID, "id_password2").send_keys(new_password)
        self.selenium.find_element(By.NAME, "_save").click()

        # 4) Ahora estamos en el change form del usuario (paso 2)
        self.wait().until(EC.presence_of_element_located((By.ID, "content")))
        self.open_all_details()

        # 5) El widget de groups suele ser FilteredSelectMultiple:
        #    id_groups_from contiene los disponibles
        try:
            self.wait().until(EC.presence_of_element_located((By.ID, "id_groups_from")))
            available = self.selenium.find_element(By.ID, "id_groups_from")
            option = available.find_element(By.XPATH, f".//option[normalize-space()='{group_name}']")
            # si llega aquí, el grupo aparece como asignable ✅
            _ = option
        except Exception:
            # fallback: a veces puede existir id_groups directamente
            try:
                groups = self.selenium.find_element(By.ID, "id_groups")
                groups.find_element(By.XPATH, f".//option[normalize-space()='{group_name}']")
            except Exception:
                raise AssertionError(
                    f"No encuentro el grupo '{group_name}' en el formulario de usuario. "
                    f"url={self.selenium.current_url} title={self.selenium.title}"
                )
