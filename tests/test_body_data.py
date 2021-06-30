from apiritif import http
from unittest import TestCase
from urllib3 import disable_warnings

disable_warnings()


class TestRequests(TestCase):
    def test_body_string(self):
        http.post('http://blazedemo.com/', data='MY PERFECT BODY')

    def test_body_json(self):
        http.post('http://blazedemo.com/', json={'foo': 'bar'})

    def test_body_files(self):
        http.post('http://blazedemo.com/', files=[('inp_file', ("filename", 'file-contents'))])

    def test_url_params(self):
        http.get('http://blazedemo.com/', params={'foo': 'bar'})
