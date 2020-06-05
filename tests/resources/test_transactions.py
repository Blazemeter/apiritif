from unittest import TestCase

import apiritif


class TestTransactions(TestCase):
    def test_1_single_transaction(self):
        with apiritif.transaction("single-transaction"):
            pass

    def test_2_two_transactions(self):
        with apiritif.transaction("transaction-1"):
            pass
        with apiritif.transaction("transaction-2"):
            pass

    def test_3_nested_transactions(self):
        with apiritif.transaction("outer"):
            with apiritif.transaction("inner"):
                pass

    def test_4_no_transactions(self):
        pass

    def test_5_apiritif_assertions(self):
        apiritif.http.get("http://blazedemo.com/").assert_ok()

    def test_6_apiritif_assertions_failed(self):
        apiritif.http.get("http://blazedemo.com/").assert_failed()  # this assertion intentionally fails

    def test_7_failed_request(self):
        apiritif.http.get("http://notexists")
