import logging
import os
from unittest import TestCase

from apiritif.feeders import CSVFeeder, Feeder
from apiritif.utils import NormalShutdown

logging.basicConfig(level=logging.DEBUG)


class TestDataFeeders(TestCase):
    def test_simple_step(self):
        vars_dict = {}
        feeder = CSVFeeder(os.path.join(os.path.dirname(__file__), "resources", "test_data.csv"), vars_dict,
                           register=False)
        self.assertEqual({}, vars_dict)
        feeder.step()
        self.assertEqual({'index': '1', 'data': 'foo'}, vars_dict)
        feeder.step()
        self.assertEqual({'index': '2', 'data': 'bar'}, vars_dict)

    def test_loop(self):
        vars_dict = {}
        feeder = CSVFeeder(os.path.join(os.path.dirname(__file__), "resources", "test_data.csv"), vars_dict,
                           register=False)
        self.assertEqual({}, vars_dict)
        feeder.step()
        self.assertEqual({'index': '1', 'data': 'foo'}, vars_dict)
        feeder.step()
        self.assertNotEqual({'index': '1', 'data': 'foo'}, vars_dict)
        feeder.step()
        feeder.step()  # fourth step should re-set it back to the beginning
        self.assertEqual({'index': '1', 'data': 'foo'}, vars_dict)

    def test_noloop(self):
        vars_dict = {}
        feeder = CSVFeeder(os.path.join(os.path.dirname(__file__), "resources", "test_data.csv"), vars_dict,
                           loop=False, register=False)
        self.assertEqual({}, vars_dict)
        feeder.step()
        feeder.step()
        feeder.step()
        self.assertRaises(NormalShutdown, feeder.step)

    def test_reopen(self):
        vars_dict = {}
        feeder = CSVFeeder(os.path.join(os.path.dirname(__file__), "resources", "test_data.csv"), vars_dict,
                           register=False)
        self.assertEqual({}, vars_dict)
        feeder.step()
        feeder.step()
        self.assertEqual({'index': '2', 'data': 'bar'}, vars_dict)
        feeder.reopen()
        feeder.step()
        self.assertEqual({'index': '1', 'data': 'foo'}, vars_dict)

    def test_step_all_feeders(self):
        vars1 = {}
        feeder1 = CSVFeeder(os.path.join(os.path.dirname(__file__), "resources", "test_data.csv"), vars1,
                           loop=False)
        vars2 = {}
        feeder2 = CSVFeeder(os.path.join(os.path.dirname(__file__), "resources", "test_data.csv"), vars2,
                           loop=False)
        Feeder.step_all_feeders()
        self.assertEqual({'index': '1', 'data': 'foo'}, vars1)
        self.assertEqual({'index': '1', 'data': 'foo'}, vars2)
        Feeder.step_all_feeders()
        self.assertEqual({'index': '2', 'data': 'bar'}, vars1)
        self.assertEqual({'index': '2', 'data': 'bar'}, vars2)
