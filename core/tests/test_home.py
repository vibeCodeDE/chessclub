from django.test import TestCase


class HomeTests(TestCase):
    def test_home_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_home_is_mobile_ready(self):
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn('name="viewport"', content)
        self.assertIn("width=device-width", content)
