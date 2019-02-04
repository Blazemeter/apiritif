import os
import unittest


import apiritif
from apiritif.thread import get_index
from apiritif.feeders import CSVReader

feeder = CSVReader(os.path.join(os.path.dirname(__file__), "data/source.csv"))


def log_it(name, data):
    log_line = "%s-%s. %s:%s\n" % (get_index(), name, data["name"], data["pass"])
    with apiritif.transaction(log_line):    # write log_line into report file for checking purposes
        pass


def setup():    # setup_module
    feeder.read_vars()  #


class Test0(unittest.TestCase):
    def test_00(self):
        log_it("00", feeder.get_vars())


class Test1(unittest.TestCase):
    def setUp(self):
        self.vars = feeder.get_vars()

    def test_10(self):
        log_it("10", self.vars)

    def test_11(self):
        log_it("11", self.vars)
