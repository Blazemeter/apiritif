import os
import unittest


import apiritif
from apiritif import thread_indexes
from apiritif.feeders import CSVFeeder

feeder = CSVFeeder(os.path.join(os.path.dirname(__file__), "data/source.csv"))
log_file = "/tmp/apiritif.log"


def log_line(name, vars):
    line = "%s-%s. %s:%s\n" % (thread_indexes()[1], name, vars["name"], vars["pass"])
    with open(log_file, "a") as lf:
        lf.write(line)


def setup():    # setup_module
    feeder.read_vars()  # todo: close reader in nose_run
    log_line("setup", feeder.get_vars())


class Test0(unittest.TestCase):
    def test_00(self):
        log_line("00", feeder.get_vars())
        with apiritif.transaction('blazedemo 123'):
            response = apiritif.http.get('http://demo.blazemeter.com/echo.php?echo=123', allow_redirects=True)


class Test1(unittest.TestCase):
    def setUp(self):
        self.vars = feeder.get_vars()

    def test_10(self):
        log_line("10", self.vars)

    def test_11(self):
        log_line("11", self.vars)


