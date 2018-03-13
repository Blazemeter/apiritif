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
        self.assertEqual(len(samples), 7)

        single = samples[0]
        self.assertEqual('test_1_single_transaction', single.test_suite)
        self.assertEqual('single-transaction', single.test_case)
        self.assertEqual(single.status, "PASSED")

        first, second = samples[1:3]
        self.assertEqual(first.status, "PASSED")
        self.assertEqual(first.test_suite, 'test_2_two_transactions')
        self.assertEqual(first.test_case, 'transaction-1')
        self.assertEqual(second.status, "PASSED")
        self.assertEqual(second.test_suite, 'test_2_two_transactions')
        self.assertEqual(second.test_case, 'transaction-2')

        nested = samples[3]
        inner = nested.subsamples[0]
        self.assertEqual('test_3_nested_transactions.outer', nested.test_suite + '.' + nested.test_case)
        self.assertEqual('outer.inner', inner.test_suite + '.' + inner.test_case)
        self.assertEqual(nested.status, "PASSED")
        self.assertEqual(inner.status, "PASSED")

        no_tran = samples[4]
        self.assertEqual(no_tran.status, "PASSED")
        self.assertEqual(no_tran.test_suite, "TestTransactions")
        self.assertEqual(no_tran.test_case, "test_4_no_transactions")

        with_assert = samples[5]
        self.assertEqual(with_assert.status, "PASSED")
        self.assertEqual(with_assert.test_suite, "test_5_apiritif_assertions")
        self.assertEqual(with_assert.test_case, "http://blazedemo.com/")
        self.assertEqual(len(with_assert.assertions), 1)
        assertion = with_assert.assertions[0]
        self.assertEqual(assertion.name, "assert_ok")
        self.assertEqual(assertion.failed, False)

        assert_failed = samples[6]
        self.assertEqual(assert_failed.status, "FAILED")
        self.assertEqual(assert_failed.test_suite, "test_6_apiritif_assertions_failed")
        self.assertEqual(assert_failed.test_case, "http://blazedemo.com/")
        self.assertEqual(len(assert_failed.assertions), 1)
        assertion = assert_failed.assertions[0]
        self.assertEqual(assertion.name, "assert_failed")
        self.assertEqual(assertion.failed, True)
        self.assertEqual(assertion.error_message, "Request to http://blazedemo.com/ didn't fail (200)")

    def test_label_single_transaction(self):
        test_file = RESOURCES_DIR + "/test_single_transaction.py"
        self.assertTrue(os.path.exists(test_file))
        writer = CachingWriter()
        nose.run(argv=[__file__, test_file, '-v'], addplugins=[Recorder(writer)])
        samples = writer.samples
        self.assertEqual(len(samples), 2)
        first, second = samples

        self.assertEqual(first.test_suite, "test_requests")
        self.assertEqual(first.test_case, "blazedemo 123")
        self.assertEqual(1, len(first.subsamples))
        first_req = first.subsamples[0]
        self.assertEqual(first_req.test_suite, "blazedemo 123")
        self.assertEqual(first_req.test_case, 'http://demo.blazemeter.com/echo.php?echo=123')

        self.assertEqual(second.test_suite, "test_requests")
        self.assertEqual(second.test_case, "blazedemo 456")
        self.assertEqual(1, len(second.subsamples))
        second_req = second.subsamples[0]
        self.assertEqual(second_req.test_suite, "blazedemo 456")
        self.assertEqual(second_req.test_case, 'http://demo.blazemeter.com/echo.php?echo=456')
