import os
import unittest

from apiritif import thread_indexes
from apiritif.feeders import CSVFeeder

feeder = CSVFeeder(os.path.join(os.path.dirname(__file__), "data/source.csv"))
log_file = "/tmp/apiritif.log"


class TestSimple(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        feeder.read_vars()

    def setUp(self):
        self.vars = feeder.get_vars()

    def test_first(self):
        log_line = "%s.first %s:%s\n" % (thread_indexes()[1], self.vars["name"], self.vars["pass"])
        with open(log_file, "a") as lf:
            lf.write(log_line)

    def test_second(self):
        log_line = "%s.second %s:%s\n" % (thread_indexes()[1], self.vars["name"], self.vars["pass"])
        with open(log_file, "a") as lf:
            lf.write(log_line)
