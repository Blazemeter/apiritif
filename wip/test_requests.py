import threading
import os
import logging
import random
import string
import sys
import time
import unittest

import os

import apiritif
from apiritif.feeders import CSVFeeder

vars = {}
data_feeder = CSVFeeder('/home/taras/Projects/apiritif/wip/cs/data.csv', vars)


class TestSimple(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data_feeder.read_vars()

    def setUp(self):
        new_vars = data_feeder.get_vars()
        for key, val in new_vars.items():
            vars[key] = val

    def test_1_httpblazedemocomnamepass(self):
        with apiritif.transaction('http://blazedemo.com/{}/{}'.format(vars['name'], vars['pass'])):
            pass
            #response = apiritif.http.get('http://blazedemo.com/{}/{}'.format(vars['name'], vars['pass']))

    def test_2_log_it(self):
        with open("/tmp/apiritif.log", "a") as _file:
            _file.write("%s:%s{%s:%s}\n" % (os.getpid(), threading.current_thread(), vars["name"], vars["pass"]))

