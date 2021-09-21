# coding=utf-8

import logging
import random
import string
import sys
import unittest
from time import time, sleep
import os
import apiritif


def write(line):
    test_result = apiritif.get_from_thread_store('test_result')
    test_result.append(line)
    apiritif.put_into_thread_store(test_result=test_result)


class TestSc1(unittest.TestCase):

    def setUp(self):
        self.vars = {}
        timeout = 2.0
        self.graceful_flag = os.environ.get('GRACEFUL')
        apiritif.put_into_thread_store(test_result=[])
        if self.graceful_flag and os.path.exists(self.graceful_flag):
            os.remove(self.graceful_flag)

        apiritif.put_into_thread_store(timeout=timeout, func_mode=True, scenario_name='sc1')

    def tearDown(self):
        if self.graceful_flag and os.path.exists(self.graceful_flag):
            os.remove(self.graceful_flag)

    def _1_httpsblazedemocomsetup1(self):
        with apiritif.smart_transaction('https://blazedemo.com/setup1'):
            write('1. setup1')
            response = apiritif.http.get('https://blazedemo.com/setup2', timeout=2.0)

    def _1_httpsblazedemocomsetup2(self):
        with apiritif.smart_transaction('https://blazedemo.com/setup2'):
            write('2. setup2')
            response = apiritif.http.get('https://blazedemo.com/setup2', timeout=2.0)

    def _2_httpsblazedemocommain1(self):
        with apiritif.smart_transaction('https://blazedemo.com/main1'):
            write('3. main1')
            response = apiritif.http.get('https://blazedemo.com/main1', timeout=2.0)

    def _2_httpsblazedemocommain2(self):
        with apiritif.smart_transaction('https://bad_url.com/main2'):
            write('4. main2')
            response = apiritif.http.get('https://blazedemo.com/main2', timeout=2.0)

    def _2_httpsblazedemocommain3(self):
        with apiritif.smart_transaction('https://blazedemo.com/main3'):
            write('XXX. main3')
            response = apiritif.http.get('https://blazedemo.com/main3', timeout=2.0)

    def _3_httpsblazedemocomteardown1(self):
        with apiritif.smart_transaction('https://blazedemo.com/teardown1'):
            write('5. teardown1')
            response = apiritif.http.get('https://blazedemo.com/teardown1', timeout=2.0)

    def _3_httpsblazedemocomteardown2(self):
        with apiritif.smart_transaction('https://blazedemo.com/teardown2'):
            write('6. teardown2')
            response = apiritif.http.get('https://blazedemo.com/teardown2', timeout=2.0)

    def test_sc1(self):
        try:
            self._1_httpsblazedemocomsetup1()
            self._1_httpsblazedemocomsetup2()
            self._2_httpsblazedemocommain1()
            self._2_httpsblazedemocommain2()
            self._2_httpsblazedemocommain3()
        finally:
            apiritif.set_stage("teardown")
            self._3_httpsblazedemocomteardown1()
            self._3_httpsblazedemocomteardown2()
