import math
import os
from unittest import TestCase

import apiritif

vars = {}
feeder = apiritif.feeders.CSVFeeder(os.path.join(os.path.dirname(__file__), "test_data.csv"), vars)


class TestCSVSimple(TestCase):
    def test_case1(self):
        with apiritif.transaction('%s-%s' % (vars['index'], vars['data'])):
            for x in range(1, 10):
                y = math.sqrt(x)
