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
            response = apiritif.http.get('https://api.demoblaze.com/entries', allow_redirects=True)
            response.assert_jsonpath('$.LastEvaluatedKey.id', expected_value='9')
        time.sleep(0.75)

        with apiritif.transaction('blazedemo 456'):
            response = apiritif.http.get('https://api.demoblaze.com/entries', allow_redirects=True)
            response.assert_jsonpath("$['LastEvaluatedKey']['id']", expected_value='9')
        time.sleep(0.75)
