from unittest import TestCase
import os

from apiritif import http


class TestResponce(TestCase):
    def test_cookies(self):
        response = http.get('http://httpbin.org/cookies/set?name=value', cookies={"foo": "bar"})
        response.assert_ok()

    def test_cert_client(self):
        # client certificate configuration. requires cert file and password. public server: https://badssl.com/
        cert = (os.path.join(os.path.dirname(__file__), "resources/data/badssl.com-client.p12"), None)
        response = http.get('http://badssl.test', cert=cert)
        response.assert_ok()

    def test_cert_server(self):
        # server certificate configuration. requires cert and key files. must have a local server to run
        cert = (os.path.join(os.path.dirname(__file__), "resources/data/server_cert.pem"),
                os.path.join(os.path.dirname(__file__), "resources/data/server_key.pem"))
        response = http.get('http://badssl.test', cert=cert)
        response.assert_ok()
