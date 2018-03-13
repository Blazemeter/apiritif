import logging
import random
import string
import sys
import time
import unittest

import apiritif



class TestAPIRequests(unittest.TestCase):

    def test_requests(self):
        with apiritif.transaction('blazedemo 123'):
            response = apiritif.http.get('http://demo.blazemeter.com/echo.php?echo=123', allow_redirects=True)
            response.assert_jsonpath('$.GET.echo', expected_value='123')
        time.sleep(0.75)

        with apiritif.transaction('blazedemo 456'):
            response = apiritif.http.get('http://demo.blazemeter.com/echo.php?echo=456', allow_redirects=True)
            response.assert_jsonpath("$['GET']['echo']", expected_value='456789')
        time.sleep(0.75)
