import copy
import logging
import os
import tempfile
import time
from unittest import TestCase

from apiritif.loadgen import Worker, Params, Supervisor

dummy_tests = [os.path.join(os.path.dirname(__file__), "test_dummy.py")]

logging.basicConfig(level=logging.DEBUG)


class TestLoadGen(TestCase):
    def test_threads_and_processes(self):
        script = os.path.dirname(os.path.realpath(__file__)) + "/resources/test_threads_and_processes.py"
        outfile = tempfile.NamedTemporaryFile()
        report = outfile.name + "-%s.csv"
        outfile.close()
        print(report)
        params = Params()
        params.concurrency = 4
        params.iterations = 2
        params.report = report
        params.tests = [script]
        params.worker_count = 2

        sup = Supervisor(params)
        sup.start()
        sup.join()

        content = []
        for i in range(params.worker_count):
            with open(report % i) as f:
                content.extend(f.readlines()[1::2])

        threads = {"0": [], "1": [], "2": [], "3": []}
        content = [item[item.index('"')+1:].strip() for item in content]
        for item in content:
            threads[item[0]].append(item[2:])

        target = {
            '0': ['00. user0:0', '10. user0:0', '11. user0:0', '00. user4:4', '10. user4:4', '11. user4:4'],
            '1': ['00. user1:1', '10. user1:1', '11. user1:1', '00. user5:5', '10. user5:5', '11. user5:5'],
            '2': ['00. user2:2', '10. user2:2', '11. user2:2', '00. user0:0', '10. user0:0', '11. user0:0'],
            '3': ['00. user3:3', '10. user3:3', '11. user3:3', '00. user1:1', '10. user1:1', '11. user1:1']}

        self.assertEqual(threads, target)

    def test_two_readers(self):
        script = os.path.dirname(os.path.realpath(__file__)) + "/resources/test_two_readers.py"
        outfile = tempfile.NamedTemporaryFile()
        report = outfile.name + "-%s.csv"
        outfile.close()
        print(report)
        params = Params()
        params.concurrency = 2
        params.iterations = 3
        params.report = report
        params.tests = [script]
        params.worker_count = 1

        sup = Supervisor(params)
        sup.start()
        sup.join()

        content = []
        for i in range(params.worker_count):
            with open(report % i) as f:
                content.extend(f.readlines()[1::2])

        threads = {"0": [], "1": []}
        content = [item[item.index('"')+1:].strip() for item in content]
        for item in content:
            threads[item[0]].append(item[2:])

        target = {
            '0': ['00. user0:0', '10. user0:0', '11. user0:0', '00. user4:4', '10. user4:4', '11. user4:4'],
            '1': ['00. user1:1', '10. user1:1', '11. user1:1', '00. user5:5', '10. user5:5', '11. user5:5'],
            '2': ['00. user2:2', '10. user2:2', '11. user2:2', '00. user0:0', '10. user0:0', '11. user0:0'],
            '3': ['00. user3:3', '10. user3:3', '11. user3:3', '00. user1:1', '10. user1:1', '11. user1:1']}

        self.assertEqual(threads, target)

    def test_thread(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        params = Params()
        params.concurrency = 2
        params.iterations = 10
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        worker.run_nose(params)

    def test_worker(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        params = Params()
        params.concurrency = 2
        params.iterations = 10
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        worker.start()
        worker.join()

    def test_supervisor(self):
        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.tests = dummy_tests
        params.report = outfile.name + "%s"
        params.concurrency = 9
        params.iterations = 5
        sup = Supervisor(params)
        sup.start()
        while sup.isAlive():
            time.sleep(1)
        pass

    def test_ramp_up1(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)

        params1 = Params()
        params1.concurrency = 50
        params1.report = outfile.name
        params1.tests = dummy_tests
        params1.ramp_up = 60
        params1.steps = 5

        params1.worker_count = 2
        params1.worker_index = 0

        worker1 = Worker(params1)
        res1 = [x.delay for x in worker1._get_thread_params()]
        print(res1)
        self.assertEquals(params1.concurrency, len(res1))

        params2 = copy.deepcopy(params1)
        params2.worker_index = 1
        worker2 = Worker(params2)
        res2 = [x.delay for x in worker2._get_thread_params()]
        print(res2)
        self.assertEquals(params2.concurrency, len(res2))

        print(sorted(res1 + res2))

    def test_ramp_up2(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)

        params1 = Params()
        params1.concurrency = 50
        params1.report = outfile.name
        params1.tests = dummy_tests
        params1.ramp_up = 60

        params1.worker_count = 1
        params1.worker_index = 0

        worker1 = Worker(params1)
        res1 = [x.delay for x in worker1._get_thread_params()]
        print(res1)
        self.assertEquals(params1.concurrency, len(res1))

    def test_unicode_ldjson(self):
        outfile = tempfile.NamedTemporaryFile(suffix=".ldjson")
        print(outfile.name)
        params = Params()
        params.concurrency = 2
        params.iterations = 1
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        worker.start()
        worker.join()

        with open(outfile.name) as fds:
            print(fds.read())
