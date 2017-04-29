from unittest import TestCase

from apiritif import http


class TestCookies(TestCase):
    def test_cookies(self):
        response = http.get('http://httpbin.org/cookies/set?name=value', cookies={"foo": "bar"})
        response.assert_ok()
