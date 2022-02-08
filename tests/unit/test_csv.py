import os
import tempfile

from unittest import TestCase
from apiritif.loadgen import Params, Supervisor
from apiritif.csv import CSVReaderPerThread, thread_data
from tests.unit import RESOURCES_DIR


class TestCSV(TestCase):
    def setUp(self):
        thread_data.csv_readers = {}

    def test_threads_and_processes(self):
        """ check if threads and processes can divide csv fairly """
        script = os.path.join(RESOURCES_DIR, "test_thread_reader.py")
        outfile = tempfile.NamedTemporaryFile()
        report = outfile.name + "-%s.csv"
        outfile.close()
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
        content = [item[item.index('"') + 1:].strip() for item in content]
        for item in content:
            self.assertEqual(item[0], item[2])  # thread equals target
            self.assertEqual("a", item[-1])  # age is the same
            if item[6] == "0":
                self.assertEqual(-1, item.find('+'))
            else:
                self.assertNotEqual(-1, item.find('+'))  # name value is modified
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
        script = os.path.join(RESOURCES_DIR, "test_two_readers.py")
        outfile = tempfile.NamedTemporaryFile()
        report = outfile.name + "-%s.csv"
        outfile.close()
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
        content = [item[item.index('"') + 1:].strip() for item in content]
        for item in content:
            threads[item[0]].append(item[2:])

        target = {  # reader1 runs two times faster
            "0": ["0. u,ser0:000:ze:00", "1. u,ser0:000:tu:22", "0. user2:2:fo:44",
                  "1. user2:2:si:66", "0. user4:4:ze:00", "1. user4:4:tu:22"],
            "1": ["0. user1:1:on:11", "1. user1:1:th:33", "0. user3:3:fi:55",
                  "1. user3:3:se:77", "0. user5:5:on:11", "1. user5:5:th:33"]}

        self.assertEqual(threads, target)

    def test_apiritif_without_loop(self):
        """ check different reading speed, fieldnames and separators """
        script = os.path.join(RESOURCES_DIR, "test_reader_no_loop.py")
        outfile = tempfile.NamedTemporaryFile()
        report = outfile.name + "-%s.csv"
        outfile.close()
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
        content = [item[item.index('"') + 1:].strip() for item in content]
        for item in content:
            threads[item[0]].append(item[2:])

        self.assertEqual(18, len(threads["0"]))

    def test_apiritif_without_loop_simple(self):
        """ check different reading speed, fieldnames and separators """
        script = os.path.join(RESOURCES_DIR, "test_simple_csv.py")
        outfile = tempfile.NamedTemporaryFile()
        report = outfile.name + "-%s.csv"
        outfile.close()
        params = Params()
        params.concurrency = 1
        params.iterations = 5
        params.report = report
        params.tests = [script]
        params.worker_count = 1

        sup = Supervisor(params)
        sup.start()
        sup.join()

        content = []
        for i in range(params.worker_count):
            with open(report % i) as f:
                content.extend(f.readlines())

        self.assertEqual(len(content), 2)
        self.assertNotIn("Data source is exhausted", content[-1])

    def test_csv_encoding(self):
        reader_utf8 = CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/encoding_utf8.csv"), loop=False)
        reader_utf16 = CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/encoding_utf16.csv"), loop=False)
        data_utf8, data_utf16 = [], []

        reader_utf8.read_vars()
        data_utf8.append(reader_utf8.get_vars())

        reader_utf16.read_vars()
        data_utf16.append(reader_utf16.get_vars())

        self.assertEqual(data_utf8, data_utf16)

    def test_csv_quoted(self):
        readers = [
            CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/quoted_utf8.csv"), loop=False),
            CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/quoted_utf16.csv"), loop=False),
            CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/unquoted_utf8.csv"), loop=False),
            CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/unquoted_utf16.csv"), loop=False)]
        readers_data = []

        for reader in readers:
            reader.read_vars()
            readers_data.append(reader.get_vars())

        result = {'ac1': '1', 'bc1': '2', 'cc1': '3'}
        for data in readers_data:
            self.assertEqual(data, result)

    def test_csv_delimiter(self):
        readers = [
            CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/encoding_utf8.csv"), loop=False),
            CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/delimiter_tab.csv"), loop=False),
            CSVReaderPerThread(os.path.join(RESOURCES_DIR, "data/delimiter_semicolon.csv"), loop=False)]
        readers_data = []

        for reader in readers:
            reader.read_vars()
            readers_data.append(reader.get_vars())

        result = {'ac1': '1', 'bc1': '2', 'cc1': '3'}
        for data in readers_data:
            self.assertEqual(data, result)
