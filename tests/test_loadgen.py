import logging
import os
import tempfile
import time
from collections import namedtuple
from unittest import TestCase

from apiritif.loadgen import Worker, Supervisor, Params

dummy_tests = [os.path.join(os.path.dirname(__file__), "test_dummy.py")]

logging.basicConfig(level=logging.DEBUG)


class TestLoadGen(TestCase):
    def test_worker(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        params = Params()
        params.concurrency = 2
        params.results_file = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        worker.start()
        worker.join()

    def test_supervisor(self):
        outfile = tempfile.NamedTemporaryFile()
        opts = namedtuple("opts", ["concurrency", "ramp_up", "iterations", "hold_for", "result_file_template", "steps"])
        sup = Supervisor(opts(2, 0, 5, 0, outfile.name + "%s", 0), dummy_tests)
        sup.start()
        while sup.isAlive():
            time.sleep(1)
        pass

    def test_ramp_up1(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)

        params = Params()
        params.concurrency = 200
        params.results_file = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        params = [x[3] for x in worker._get_thread_params()]
        print(len(params))
        print(params)
        self.assertEquals(200, len(params))
