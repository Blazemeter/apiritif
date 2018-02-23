from unittest import TestCase

import apiritif


class TestTransactions(TestCase):
    def test_single_transaction(self):
        with apiritif.transaction("single-transaction"):
            pass

    def test_two_transactions(self):
        with apiritif.transaction("transaction-1"):
            pass
        with apiritif.transaction("transaction-2"):
            pass

    def test_nested_transactions(self):
        with apiritif.transaction("outer"):
            with apiritif.transaction("inner"):
                pass
