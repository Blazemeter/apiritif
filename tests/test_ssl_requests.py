import OpenSSL
from unittest import TestCase
from apiritif.http import http
from nose.tools import raises


# TODO: This class contains integration tests. Need to be removed in future
class TestSSL(TestCase):
    def setUp(self):
        self.host = 'client.badssl.com'
        self.request_url = 'https://client.badssl.com/'
        self.certificate_file_pem = 'certificates/badssl.com-client.pem'
        self.certificate_file_p12 = 'certificates/badssl.com-client.p12'
        self.passphrase = 'badssl.com'

    def test_get_with_encrypted_p12_certificate(self):
        encrypted_cert = (self.certificate_file_p12, self.passphrase)
        response = http.get(self.request_url, encrypted_cert=encrypted_cert)
        self.assertEqual(200, response.status_code)

    def test_get_with_encrypted_pem_certificate(self):
        encrypted_cert = (self.certificate_file_pem, self.passphrase)
        response = http.get(self.request_url, encrypted_cert=encrypted_cert)
        self.assertEqual(200, response.status_code)

    def test_get_with_incorrect_certificate(self):
        certificate_file_pem_incorrect = 'certificates/badssl.com-client-wrong.pem'
        encrypted_cert = (certificate_file_pem_incorrect, self.passphrase)
        response = http.get(self.request_url, encrypted_cert=encrypted_cert)
        self.assertEqual(400, response.status_code)

    @raises(OpenSSL.crypto.Error)
    def test_get_with_incorrect_secret(self):
        wrong_certificate_secret = 'you shall not pass'
        encrypted_cert = (self.certificate_file_pem, wrong_certificate_secret)
        response = http.get(self.request_url, encrypted_cert=encrypted_cert)

    def test_get_with_ssl_and_wrong_url(self):
        cert_missing_url = 'https://client-cert-missing.badssl.com/'
        encrypted_cert = (self.certificate_file_p12, self.passphrase)
        response = http.get(cert_missing_url, encrypted_cert=encrypted_cert)
        self.assertEqual(400, response.status_code)