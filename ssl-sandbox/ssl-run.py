host = 'client.badssl.com'
request_url = 'https://client.badssl.com/'
certificate_file_pem = 'badssl.com-client.pem'
certificate_file_p12 = 'badssl.com-client.p12'
certificate_secret = 'badssl.com'


def connect_with_httpclient():
    import http.client
    import ssl

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.load_cert_chain(certfile=certificate_file_pem, password=certificate_secret)

    connection = http.client.HTTPSConnection(host, port=443, context=context)

    connection.request(method="GET", url=request_url)

    response = connection.getresponse()
    print(response.status, response.reason)
    data = response.read()
    print(data)


def connect_with_openssl():
    import OpenSSL
    import socket

    cert_data = None
    cert_pass = certificate_secret.encode('utf8')
    with open(certificate_file_p12, 'rb') as pkcs12_file:
        cert_data = pkcs12_file.read()

    p12 = OpenSSL.crypto.load_pkcs12(cert_data, cert_pass)
    cert = p12.get_certificate()

    context = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
    context.use_certificate(cert)

    ca_certs = p12.get_ca_certificates()
    if ca_certs:
        for ca_cert in ca_certs:
            context.add_extra_chain_cert(ca_cert)
    context.use_privatekey(p12.get_privatekey())

    connection = OpenSSL.SSL.Connection(context, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    connection.set_tlsext_host_name(host.encode('utf8'))

    connection.connect((host, 443))

    connection.send('GET / HTTP/1.1\r\n'
                    'User-Agent: python-requests/2.24.0\r\n'
                    'HOST: ' + host + '\r\n'
                    'Accept-Encoding: gzip, deflate\r\n'
                    'Connection: Keep-Alive\r\n'
                    '\r\n')
    print(connection.recv(1024))


def connect_with_ssl():
    import ssl
    import socket

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.load_cert_chain(certfile=certificate_file_pem, password=certificate_secret)

    sock = socket.create_connection((host, 443))
    ssl_sock = context.wrap_socket(sock, server_hostname=host)

    ssl_sock.send(('GET / HTTP/1.1\r\n'
                   'User-Agent: python-requests/2.24.0\r\n'
                   'HOST: ' + host + '\r\n'
                   'Accept-Encoding: gzip, deflate\r\n'
                   'Connection: Keep-Alive\r\n'
                   '\r\n').encode('utf8'))
    print(ssl_sock.read(1024))

    ssl_sock.close()
