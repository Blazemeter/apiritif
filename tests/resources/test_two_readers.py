import os
import unittest


import apiritif
from apiritif.thread import get_index
from apiritif.csv import CSVReaderPerThread

reader0 = CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "data/source0.csv"), quoted=True)
reader1 = CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "data/source1.csv"),
                             fieldnames=["name+", "pass+"],
                             delimiter="-")


def log_it(name, data):
    variables = ":".join((data["name"], data["pass"], data["name+"], data["pass+"]))
    log_line = "%s-%s. %s\n" % (get_index(), name, variables)
    with apiritif.transaction(log_line):    # write log_line into report file for checking purposes
        pass


def setUpModule():    # setup_module
    reader0.read_vars()
    reader1.read_vars()


class Test1(unittest.TestCase):
    def setUp(self):
        self.vars = {}
        self.vars.update(reader0.get_vars())
        self.vars.update(reader1.get_vars())

    def test_0(self):
        log_it("0", self.vars)
        reader1.read_vars()

    def test_1(self):
        log_it("1", self.vars)
