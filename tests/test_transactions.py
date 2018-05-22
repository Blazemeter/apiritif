import logging
import time
import unittest

from apiritif import http, transaction, transaction_logged

target = http.target('https://jsonplaceholder.typicode.com')
target.keep_alive(True)
target.auto_assert_ok(False)
target.use_cookies(True)


class TestRequests(unittest.TestCase):
    # will produce test-case sample with one sub-sample
    def test_1_single_request(self):
        target.get('/')

    # will produce test-case sample with two sub-samples
    def test_2_multiple_requests(self):
        target.get('/')
        target.get('/2')

    # won't produce test-case sample, only transaction
    def test_3_toplevel_transaction(self):
        with transaction("Transaction"):
            target.get('/')
            target.get('/2')

    # won't produce test-case sample, only "Tran Name"
    # will also will skip "GET /" request, as it's not in the transaction.
    def test_4_mixed_transaction(self):
        target.get('/')
        with transaction("Transaction"):
            target.get('/2')

    # won't produce test-case sample, two separate ones
    def test_5_multiple_transactions(self):
        with transaction("Transaction 1"):
            target.get('/')
            target.get('/2')

        with transaction("Transaction 2"):
            target.get('/')
            target.get('/2')

    def test_6_transaction_obj(self):
        tran = transaction("Label")
        tran.start()
        time.sleep(0.5)
        tran.finish()

    def test_7_transaction_fail(self):
        with transaction("Label") as tran:
            tran.fail("Something went wrong")

    def test_8_transaction_attach(self):
        with transaction("Label") as tran:
            user_input = "YO"
            tran.set_request("Request body")
            tran.set_response("Response body")
            tran.set_response_code(201)
            tran.attach_extra("user", user_input)

    def test_9_transaction_logged(self):
        with transaction_logged("Label") as tran:
            logging.warning("TODO: capture logging to assert for result")