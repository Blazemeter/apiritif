import logging
import random
import string
import sys
import time
import unittest

import apiritif


class TestTwoTransactions(unittest.TestCase):

    def first(self):
        with apiritif.smart_transaction('first transaction'):
            response = apiritif.http.get('https://blazedemo.com/')
            response.assert_ok()

    def second(self):
        with apiritif.smart_transaction('second transaction'):
            response = apiritif.http.get('https://blazedemo.com/vacation.html')

    def test_simple(self):
        self.first()
        self.second()
