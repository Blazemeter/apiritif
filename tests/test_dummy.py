import math
import time
from unittest import TestCase


class TestSimple(TestCase):
    def test_case1(self):
        for x in range(1, 10000):
            y = math.sqrt(x)

    def test_case2(self):
        for x in range(1, 1000):
            y = math.sqrt(x)
