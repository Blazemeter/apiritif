import logging
import random
import string
import sys
import time
import unittest

import apiritif


class TestTwoTransactions(unittest.TestCase):

    def transaction_simple(self):
        with apiritif.transaction('simple transaction'):
            response = apiritif.http.get('https://blazedemo.com/')

    def transaction_smart(self):
        with apiritif.smart_transaction('smart transaction'):
            response = apiritif.http.get('https://blazedemo.com/vacation.html')

    def test_simple(self):
        self.transaction_simple()
        self.transaction_smart()
