import logging
import time
import unittest
import threading
import apiritif

from urllib3 import disable_warnings
from apiritif import http, transaction, transaction_logged, smart_transaction

target = http.target('https://httpbin.org')
target.keep_alive(True)
target.auto_assert_ok(False)
target.use_cookies(True)
disable_warnings()


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


class ControllerMock(object):
    class CurrentSampleMock:
        def __init__(self, index):
            self.test_case = 'TestCase %d' % index
            self.test_suite = 'TestSuite %d' % index

    def __init__(self, index):
        self.tran_mode = True
        self.test_info = {}
        self.current_sample = self.CurrentSampleMock(index)

    def beforeTest(self):
        pass

    def startTest(self):
        pass

    def stopTest(self, is_transaction):
        pass

    def addError(self, name, msg, trace, is_transaction):
        pass

    def afterTest(self, is_transaction):
        pass


class TransactionThread(threading.Thread):
    def __init__(self, index):
        self.index = index
        self.driver = 'Driver %d' % self.index
        self.controller = ControllerMock(self.index)

        self.thread_name = 'Transaction %d' % self.index
        self.exception_message = 'Thread %d failed' % self.index

        super(TransactionThread, self).__init__(target=self._run_transaction)

    def _run_transaction(self):
        apiritif.put_into_thread_store(driver=self.driver, func_mode=False, controller=self.controller)
        apiritif.set_transaction_handlers({'enter': [self._enter_handler], 'exit': [self._exit_handler]})

        tran = smart_transaction(self.thread_name)
        with tran:
            self.transaction_driver = tran.driver
            self.transaction_controller = tran.controller
            raise Exception(self.exception_message)

        self.message_from_thread_store = apiritif.get_from_thread_store('message')

    def _enter_handler(self):
        pass

    def _exit_handler(self):
        pass


class TestMultiThreadTransaction(unittest.TestCase):

    # Transaction data should be different for each thread.
    # Here TransactionThread class puts all transaction data into thread store.
    # Then we save all thread data from real transaction data to our mock.
    # As the result written and saved data should be the same.
    def test_Transaction_data_per_thread(self):
        transactions = [TransactionThread(i) for i in range(5)]

        for tran in transactions:
            tran.start()
        for tran in transactions:
            tran.join()
        for tran in transactions:
            self.assertEqual(tran.transaction_controller, tran.controller)
            self.assertEqual(tran.transaction_driver, tran.driver)
            self.assertEqual(tran.message_from_thread_store, tran.exception_message)
