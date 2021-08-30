# coding=utf-8
import unittest
import apiritif
from apiritif import get_transaction_handlers, set_transaction_handlers


def add_dummy_handlers():
    handlers = get_transaction_handlers()
    handlers["enter"].append(_enter_handler)
    handlers["exit"].append(_exit_handler)
    set_transaction_handlers(handlers)


def _enter_handler():
    pass


def _exit_handler():
    pass


class Driver(object):
    def get(self, addr):
        pass

    def quit(self):
        pass


class TestSmartTransactions(unittest.TestCase):
    def setUp(self):
        self.driver = None
        self.driver = Driver()
        add_dummy_handlers()
        self.vars = {

        }

        apiritif.put_into_thread_store(
            driver=self.driver,
            func_mode=False)  # don't stop after failed test case

    def _1_t1(self):
        with apiritif.smart_transaction('t1'):
            self.driver.get('addr1')

    def _2_t2(self):
        with apiritif.smart_transaction('t2'):
            self.driver.get('addr2')

    def _3_t3(self):
        with apiritif.smart_transaction('t3'):
            self.driver.get('addr3')

    def test_smartTransactions(self):
        self._1_t1()
        self._2_t2()
        #self._3_t3()

    def tearDown(self):
        if self.driver:
            self.driver.quit()
