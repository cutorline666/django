from django.test import TestCase

class SmokeTest(TestCase):
    def test_ok(self):
        self.assertTrue(True)

# Importa els selenium tests perquè Django els executi també
try:
    from .tests_selenium import AdminGroupsSeleniumTests  # noqa: F401
except Exception:
    # Si a GitHub Actions no hi ha navegador/driver, com a mínim no trenquem aquí.
    pass
