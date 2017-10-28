import copy
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

        params1 = Params()
        params1.concurrency = 50
        params1.results_file = outfile.name
        params1.tests = dummy_tests
        params1.ramp_up = 60
        params1.steps = 5

        params1.worker_count = 2
        params1.worker_index = 0

        worker1 = Worker(params1)
        res1 = [x[3] for x in worker1._get_thread_params()]
        print(res1)
        self.assertEquals(params1.concurrency, len(res1))

        params2 = copy.deepcopy(params1)
        params2.worker_index = 1
        worker2 = Worker(params2)
        res2 = [x[3] for x in worker2._get_thread_params()]
        print(res2)
        self.assertEquals(params2.concurrency, len(res2))

        print(sorted(res1 + res2))

    def test_ramp_up2(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)

        params1 = Params()
        params1.concurrency = 50
        params1.results_file = outfile.name
        params1.tests = dummy_tests
        params1.ramp_up = 60

        params1.worker_count = 1
        params1.worker_index = 0

        worker1 = Worker(params1)
        res1 = [x[3] for x in worker1._get_thread_params()]
        print(res1)
        self.assertEquals(params1.concurrency, len(res1))