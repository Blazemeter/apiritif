import logging
import os
import tempfile
import time
from collections import namedtuple
from unittest import TestCase

from apiritif.loadgen import Worker, Supervisor

dummy_tests = [os.path.join(os.path.dirname(__file__), "test_dummy.py")]

logging.basicConfig(level=logging.DEBUG)


class TestLoadGen(TestCase):
    def test_worker(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        worker = Worker(2, outfile.name, dummy_tests, 2)
        worker.start()
        worker.join()

    def test_supervisor(self):
        outfile = tempfile.NamedTemporaryFile()
        opts = namedtuple("opts", ["concurrency", "ramp_up", "iterations", "hold_for", "result_file_template"])
        sup = Supervisor(opts(2, 0, 5, 0, outfile.name + "%s"), dummy_tests)
        sup.start()
        while sup.isAlive():
            time.sleep(1)
        pass
