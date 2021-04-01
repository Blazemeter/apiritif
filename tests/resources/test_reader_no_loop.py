import os
import unittest


import apiritif
from apiritif.context import get_index, get_iteration
from apiritif.csv import CSVReaderPerThread

reader = CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "data/source0.csv"), loop=False)


def log_it(name, data):
    log_line = "%s-%s. %s:%s\n" % (get_index(), name, data["name"], data["pass"])
    with apiritif.transaction(log_line):    # write log_line into report file for checking purposes
        pass


def setup():    # setup_module
    if get_iteration() > 6:     # do one pass to set stop_cause once
        return

    reader.read_vars()  #


class Test0(unittest.TestCase):
    def test_00(self):
        log_it("00", reader.get_vars())
        if get_iteration() > 5:
            raise BaseException("!!!")


class Test1(unittest.TestCase):
    def setUp(self):
        self.vars = reader.get_vars()

    def test_10(self):
        log_it("10", self.vars)

    def test_11(self):
        log_it("11", self.vars)
