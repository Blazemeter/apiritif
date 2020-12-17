host = 'client.badssl.com'
request_url = 'https://client.badssl.com/'
certificate_file_pem = 'badssl.com-client.pem'
certificate_file_p12 = 'badssl.com-client.p12'
certificate_secret = 'badssl.com'


def connect_with_requests():
    import requests

    r = requests.get(request_url, verify=certificate_file_pem)

    print(r)
    print(r.content)


def connect_with_urllib3():
    import urllib3

    conn = urllib3.connection_from_url(
        request_url,
        ca_certs=certificate_file_pem,
        key_password=certificate_secret,
        cert_reqs='REQUIRED')

    print(conn.request('get', request_url))


def connect_with_httpclient():  # working approach
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


connect_with_httpclient()


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
    context.use_privatekey(p12.get_privatekey())

    connection = OpenSSL.SSL.Connection(context, socket.socket())

    connection.connect((host, 443))

    print(connection.write("hello there"))
    print(connection.recv(1024))


def connect_with_ssl():
    import ssl
    import socket

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.load_cert_chain(certfile=certificate_file_pem, password=certificate_secret)

    sock = socket.create_connection((host, 443))
    ssl_sock = context.wrap_socket(sock, server_hostname=host)

    ssl_sock.send("hello there".encode('utf8'))
    print(ssl_sock.recv(1024))

    ssl_sock.close()
