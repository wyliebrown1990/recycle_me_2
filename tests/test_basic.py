# tests/test_basic.py

import unittest
from app.recycle_me import app

class BasicTests(unittest.TestCase):
    # executed prior to each test
    def setUp(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        self.app = app.test_client()

    # executed after each test
    def tearDown(self):
        pass

    # Tests
    def test_main_page(self):
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_invalid_route(self):
        response = self.app.get('/something', follow_redirects=True)
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
