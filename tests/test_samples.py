import os
from unittest import TestCase

import nose

from apiritif.loadgen import ApiritifPlugin

RESOURCES_DIR = os.path.dirname(os.path.realpath(__file__)) + "/resources"


class CachingWriter(object):
    def __init__(self):
        self.samples = []

    def add(self, sample, test_count, success_count):
        print(sample, test_count, success_count )
        self.samples.append(sample)


class Recorder(ApiritifPlugin):
    def configure(self, options, conf):
        super(Recorder, self).configure(options, conf)
        self.enabled = True


class TestSamples(TestCase):
    def test_transactions(self):
        test_file = RESOURCES_DIR + "/test_transactions.py"
        self.assertTrue(os.path.exists(test_file))
        writer = CachingWriter()
        nose.run(argv=[__file__, test_file, '-v'], addplugins=[Recorder(writer)])
        samples = writer.samples
        self.assertEqual(len(samples), 4)

        nested = samples[0]
        inner = nested.subsamples[0]
        self.assertEqual('test_nested_transactions.outer', nested.test_suite + '.' + nested.test_case)
        self.assertEqual('outer.inner', inner.test_suite + '.' + inner.test_case)
        self.assertEqual(nested.status, "PASSED")
        self.assertEqual(inner.status, "PASSED")

        single = samples[1]
        self.assertEqual('test_single_transaction', single.test_suite)
        self.assertEqual('single-transaction', single.test_case)
        self.assertEqual(single.status, "PASSED")

        first, second = samples[2:4]
        self.assertEqual(first.status, "PASSED")
        self.assertEqual(first.test_suite, 'test_two_transactions')
        self.assertEqual(first.test_case, 'transaction-1')
        self.assertEqual(second.status, "PASSED")
        self.assertEqual(second.test_suite, 'test_two_transactions')
        self.assertEqual(second.test_case, 'transaction-2')
