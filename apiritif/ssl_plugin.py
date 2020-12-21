import os
import OpenSSL
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.contrib.pyopenssl import PyOpenSSLContext

try:
    from ssl import PROTOCOL_TLS as ssl_protocol
except ImportError:
    from ssl import PROTOCOL_SSLv23 as ssl_protocol


class SSLPlugin:
    @staticmethod
    def use_encrypted_certificate(session, certificate_file_path, passphrase):
        """
        :param session: requests.Session
        :param certificate_file_path: str
        :param passphrase: str
        """

        pkcs12_obj = SSLPlugin.create_pkcs12_obj(certificate_file_path, passphrase)
        ssl_context = SSLPlugin.create_ssl_context(pkcs12_obj)
        pkcs12_adapter = Pkcs12Adapter(ssl_context=ssl_context)
        session.mount('https://', pkcs12_adapter)

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
            pkcs12_obj = SSLPlugin._create_openssl_cert_from_pem(certificate_data, certificate_password)
        else:
            pkcs12_obj = SSLPlugin._create_openssl_cert_from_pkcs12(certificate_data, passphrase)

        return pkcs12_obj

    @staticmethod
    def create_ssl_context(pkcs12_cert):
        """
        :param pkcs12_cert: OpenSSL.crypto.PKCS12
        :return: context
        :rtype: urllib3.contrib.pyopenssl.PyOpenSSLContext
        """

        cert = pkcs12_cert.get_certificate()
        SSLPlugin._check_cert_not_expired(cert)

        context = PyOpenSSLContext(ssl_protocol)
        context.ctx.use_certificate(cert)

        ca_certs = pkcs12_cert.get_ca_certificates()
        if ca_certs:
            for ca_cert in ca_certs:
                SSLPlugin._check_cert_not_expired(ca_cert)
                context.ctx.add_extra_chain_cert(ca_cert)

        context.ctx.use_privatekey(pkcs12_cert.get_privatekey())

        return context

    @staticmethod
    def _check_cert_not_expired(cert):
        cert_not_after = datetime.strptime(cert.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ')
        if cert_not_after < datetime.utcnow():
            raise ValueError('SSL certificate expired')

    @staticmethod
    def _create_openssl_cert_from_pkcs12(certificate_data, certificate_password):
        return OpenSSL.crypto.load_pkcs12(certificate_data, certificate_password)

    @staticmethod
    def _create_openssl_cert_from_pem(certificate_data, certificate_password):
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate_data)
        key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, certificate_data, passphrase=certificate_password)

        pkcs = OpenSSL.crypto.PKCS12()
        pkcs.set_privatekey(key)
        pkcs.set_certificate(cert)
        return pkcs


class Pkcs12Adapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.ssl_context = kwargs.pop('ssl_context', None)
        super(Pkcs12Adapter, self).__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        if self.ssl_context:
            kwargs['ssl_context'] = self.ssl_context
        return super(Pkcs12Adapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        if self.ssl_context:
            kwargs['ssl_context'] = self.ssl_context
        return super(Pkcs12Adapter, self).proxy_manager_for(*args, **kwargs)
