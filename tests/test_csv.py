import os
import tempfile

from unittest import TestCase
from apiritif.loadgen import Params, Supervisor, ApiritifPlugin
from apiritif.csv import CSVReaderPerThread
from apiritif.utils import NormalShutdown


class TestCSV(TestCase):
    def test_threads_and_processes(self):
        """ check if threads and processes can divide csv fairly """
        script = os.path.dirname(os.path.realpath(__file__)) + "/resources/test_thread_reader.py"
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
            self.assertEqual(item[0], item[2])  # thread equals target
            self.assertEqual("a", item[-1])     # age is the same
            if item[6] == "0":
                self.assertEqual(-1, item.find('+'))
            else:
                self.assertNotEqual(-1, item.find('+'))     # name value is modified
            threads[item[0]].append(item[9:-2])

        # format: <user>:<pass>, quoting ignored
        target = {
            '0': ['""u:ser0""', '""u+:ser0""', 'user4:4', 'user4+:4'],
            '1': ['""user1"":1', '""user1""+:1', 'user5:5', 'user5+:5'],
            '2': ['user2:""2""', 'user2+:""2""', '""u:ser0""', '""u+:ser0""'],
            '3': ['user3:3', 'user3+:3', '""user1"":1', '""user1""+:1']}

        self.assertEqual(threads, target)

    def test_two_readers(self):
        """ check different reading speed, fieldnames and separators """
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

        target = {  # reader1 runs two times faster
            "0": ["0. u,ser0:000:ze:00", "1. u,ser0:000:tu:22", "0. user2:2:fo:44",
                  "1. user2:2:si:66", "0. user4:4:ze:00", "1. user4:4:tu:22"],
            "1": ["0. user1:1:on:11", "1. user1:1:th:33", "0. user3:3:fi:55",
                  "1. user3:3:se:77", "0. user5:5:on:11", "1. user5:5:th:33"]}

        self.assertEqual(threads, target)

    def test_reader_without_loop(self):
        """ check different reading speed, fieldnames and separators """
        reader = CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "resources/data/source0.csv"), loop=False)
        data = []
        try:
            for i in range(20):
                reader.read_vars()
                data.append(reader.get_vars())
        except NormalShutdown:
            self.assertEqual(6, len(data))
            return

        self.fail()

    def test_apiritif_without_loop(self):
        """ check different reading speed, fieldnames and separators """
        script = os.path.dirname(os.path.realpath(__file__)) + "/resources/test_reader_no_loop.py"
        outfile = tempfile.NamedTemporaryFile()
        report = outfile.name + "-%s.csv"
        outfile.close()
        print(report)
        params = Params()
        params.concurrency = 1
        params.iterations = 10
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

        threads = {"0": []}
        content = [item[item.index('"')+1:].strip() for item in content]
        for item in content:
            threads[item[0]].append(item[2:])

        self.assertEqual(18, len(threads["0"]))

    def test_reader_without_loop_non_stop(self):
        """ check different reading speed, fieldnames and separators """
        script = os.path.dirname(os.path.realpath(__file__)) + "/resources/test_reader_no_loop.py"
        outfile = tempfile.NamedTemporaryFile()
        report = outfile.name + "-%s.csv"
        outfile.close()
        print(report)
        params = Params()
        params.concurrency = 1
        params.iterations = 10
        params.report = report
        params.tests = [script]
        params.worker_count = 1

        handler = ApiritifPlugin.handleError
        try:
            # wrong handler: doesn't stop iterations
            ApiritifPlugin.handleError = lambda a, b, c: False

            sup = Supervisor(params)
            sup.start()
            sup.join()
        finally:
            ApiritifPlugin.handleError = handler

        content = []
        for i in range(params.worker_count):
            with open(report % i) as f:
                content.extend(f.readlines()[1::2])

        threads = {"0": []}
        content = [item[item.index('"')+1:].strip() for item in content]
        for item in content:
            threads[item[0]].append(item[2:])

        self.assertTrue(len(threads["0"]) > 18)

    def test_reader_bom_first(self):
        """ check if BOM is ignored """
        reader_bom = CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "resources/data/source_BOM.csv"), loop=False)
        reader_no_bom = CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "resources/data/source_no_BOM.csv"), loop=False)
        data_bom, data_no_bom = [], []

        reader_bom.read_vars()
        data_bom.append(reader_bom.get_vars())

        reader_no_bom.read_vars()
        data_no_bom.append(reader_no_bom.get_vars())

        self.assertEqual(data_bom, data_no_bom)
