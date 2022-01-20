import math
from unittest import TestCase

import apiritif


def setUpModule():
    raise BaseException


class TestSimple(TestCase):
    def test_case1(self):
        #apiritif.http.get("http://localhost:8003")
        with apiritif.transaction("tran name"):
            for x in range(1000, 10000):
                y = math.sqrt(x)

