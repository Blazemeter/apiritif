import math
import time
from unittest import TestCase

import apiritif


class MyException(BaseException):
    pass


def setUpModule():
    raise ValueError()


class TestSimple(TestCase):
    def test_case1(self):
        #apiritif.http.get("http://localhost:8003")
        with apiritif.transaction("tran name"):
            for x in range(1000, 10000):
                y = math.sqrt(x)

