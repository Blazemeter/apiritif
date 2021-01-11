"""
This is a toplevel package of Apiritif tool

Copyright 2021 BlazeMeter Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
from OpenSSL import crypto
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.contrib.pyopenssl import PyOpenSSLContext

try:
    from ssl import PROTOCOL_TLS as ssl_protocol
except ImportError:
    from ssl import PROTOCOL_SSLv23 as ssl_protocol


class SSLAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        certificate_file_path = kwargs.pop('certificate_file_path', None)
        passphrase = kwargs.pop('passphrase', None)

        pkcs12_obj = CertificateReader.create_pkcs12_obj(certificate_file_path, passphrase)
        self.ssl_context = CertificateReader.create_ssl_context(pkcs12_obj)

        super(SSLAdapter, self).__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        if self.ssl_context:
            kwargs['ssl_context'] = self.ssl_context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        if self.ssl_context:
            kwargs['ssl_context'] = self.ssl_context
        return super(SSLAdapter, self).proxy_manager_for(*args, **kwargs)


class CertificateReader:
    @staticmethod
    def create_pkcs12_obj(certificate_file_path, passphrase):
        """
        :param certificate_file_path: str
        :param passphrase: str
        :return: pkcs12_obj
        :rtype: OpenSSL.crypto.PKCS12
        """

        certificate_password = passphrase.encode('utf8')
        with open(certificate_file_path, 'rb') as pkcs12_file:
            certificate_data = pkcs12_file.read()

        if os.path.splitext(certificate_file_path)[-1].lower() == '.pem':
            pkcs12_obj = CertificateReader._create_openssl_cert_from_pem(certificate_data, certificate_password)
        else:
            pkcs12_obj = CertificateReader._create_openssl_cert_from_pkcs12(certificate_data, certificate_password)

        return pkcs12_obj

    @staticmethod
    def create_ssl_context(pkcs12_cert):
        """
        :param pkcs12_cert: OpenSSL.crypto.PKCS12
        :return: context
        :rtype: urllib3.contrib.pyopenssl.PyOpenSSLContext
        """

        cert = pkcs12_cert.get_certificate()
        CertificateReader._check_cert_not_expired(cert)

        context = PyOpenSSLContext(ssl_protocol)
        context._ctx.use_certificate(cert)

        ca_certs = pkcs12_cert.get_ca_certificates()
        if ca_certs:
            for ca_cert in ca_certs:
                CertificateReader._check_cert_not_expired(ca_cert)
                context._ctx.add_extra_chain_cert(ca_cert)

        context._ctx.use_privatekey(pkcs12_cert.get_privatekey())

        return context

    @staticmethod
    def _check_cert_not_expired(cert):
        cert_not_after = datetime.strptime(cert.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ')
        if cert_not_after < datetime.utcnow():
            raise ValueError('SSL certificate expired')

    @staticmethod
    def _create_openssl_cert_from_pem(certificate_data, certificate_password):
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, certificate_data)
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, certificate_data, passphrase=certificate_password)

        pkcs = crypto.PKCS12()
        pkcs.set_privatekey(key)
        pkcs.set_certificate(cert)
        return pkcs

    @staticmethod
    def _create_openssl_cert_from_pkcs12(certificate_data, certificate_password):
        return crypto.load_pkcs12(certificate_data, certificate_password)
