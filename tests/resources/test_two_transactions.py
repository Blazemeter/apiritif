import logging
import random
import string
import sys
import time
import unittest

import apiritif


class TestTwoTransactions(unittest.TestCase):

    def first1(self):
        with apiritif.transaction('first'):
            response = apiritif.http.get('https://blazedemo.com/')
            response.assert_ok()

    def second1(self):
        with apiritif.transaction('second'):
            response = apiritif.http.get('https://blazedemo.com/vacation.html')

    def test_simple(self):
        self.first1()
        self.second1()
