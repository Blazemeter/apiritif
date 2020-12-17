import requests

# s = requests.Session()
# s.verify = 'badssl.com-client.pem'
# r = requests.get('https://client-cert-missing.badssl.com/')


r = requests.get('https://client.badssl.com/', verify='.')


print(r)
print(r.content)






# import OpenSSL
# import socket
#
#
# context = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
# context.use_certificate_file('badssl.com-client.pem')
#
# connection = OpenSSL.SSL.Connection(context, socket.socket())
# print(connection.get_certificate())
#
#
# connection.connect_ex(('client.badssl.com', 443))
#
# connection.do_handshake()
#
# print(connection.write("hello there"))
# print(connection.recv(1024))







# import ssl
# import socket
#
#
# sock = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM),
#                        ca_certs='badssl.com-client.pem',
#                        cert_reqs=ssl.CERT_REQUIRED)
# sock.connect(('client.badssl.com', 443))
# sock.close()
#
