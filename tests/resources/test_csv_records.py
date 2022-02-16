# coding=utf-8
import time
import unittest
import apiritif
import os

reader_1 = apiritif.CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "data/source2.csv"),
                                       fieldnames=['name'], loop=False, quoted=True, delimiter=',')


class TestStopByCSVRecords(unittest.TestCase):

    def setUp(self):
        self.vars = {}
        reader_1.read_vars()
        self.vars.update(reader_1.get_vars())

    def test_stop_by_csv(self):
        name = f"{apiritif.thread.get_index()}:{self.vars['name']}"
        with apiritif.smart_transaction(name):
            time.sleep(0.1)     # time for initialization and feeding next VU
