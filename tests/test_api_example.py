from apiritif import http
from unittest import TestCase
from urllib3 import disable_warnings

target = http.target("http://blazedemo.com")
target.use_cookies(False)
target.auto_assert_ok(False)
disable_warnings()


class TestSimple(TestCase):
    def test_blazedemo_index(self):
        response = target.get("/")
        response.assert_ok()

    def test_blazedemo_not_found(self):
        response = target.get("/not-found")
        response.assert_failed()
