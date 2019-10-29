import os
import unittest


import apiritif
from apiritif.store import get_index

reader_1 = apiritif.CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "data/source0.csv"))


def log_it(name, target, data):
    log_line = "%s[%s]-%s. %s:%s:%s\n" % (get_index(), target, name, data["name"], data["pass"], data["age"])
    with apiritif.transaction(log_line):    # write log_line into report file for checking purposes
        pass


def setup():    # setup_module
    target = str(get_index())

    vars = {
        'name': 'nobody',
        'age': 'a'
    }
    reader_1.read_vars()
    vars.update(reader_1.get_vars())

    apiritif.put_into_thread_store(vars, target)


# class Test0(unittest.TestCase):
#     def test_00(self):
#         log_it("00", reader_1.get_vars())


class Test1(unittest.TestCase):
    def setUp(self):
        self.vars, self.target = apiritif.get_from_thread_store()

    def test_10(self):
        log_it("10", self.target, self.vars)
        self.vars["name"] += "+"

    def test_11(self):
        log_it("11", self.target, self.vars)
