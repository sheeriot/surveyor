from django.test import SimpleTestCase
# from django.urls import reverse
# from icecream import ic


class HomepageTests(SimpleTestCase):

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to the RF Field Surveryor Tool!")

    def test_loginpage(self):
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login")

    def test_joinpage(self):
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm Password")
