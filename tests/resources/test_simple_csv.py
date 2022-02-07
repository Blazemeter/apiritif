# coding=utf-8
import unittest
import apiritif
import os

reader_1 = apiritif.CSVReaderPerThread(os.path.join(os.path.dirname(__file__), "data/source2.csv"),
                                       fieldnames=['name'], loop=False, quoted=True, delimiter=',')


class TestSimple(unittest.TestCase):

    def setUp(self):
        self.vars = {}
        reader_1.read_vars()
        self.vars.update(reader_1.get_vars())

    def test_simple(self):
        with apiritif.smart_transaction('TestSimple'):
            print(self.vars['name'])
