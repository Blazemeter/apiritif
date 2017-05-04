import unittest
from datetime import datetime

from apiritif import utilities


class TestUtilities(unittest.TestCase):
    def test_random_uniform(self):
        for _ in range(1000):
            random = utilities.random_uniform(1, 10)
            self.assertTrue(1 <= random < 10)

    def test_random_normal(self):
        for _ in range(1000):
            random = utilities.random_gauss(0, 1)
            self.assertTrue(-5 <= random < 5)

    def test_random_string(self):
        for _ in range(1000):
            random_str = utilities.random_string(10)
            self.assertEqual(10, len(random_str))
            self.assertIsInstance(random_str, str)

    def test_random_string_chars(self):
        hex_chars = "0123456789abcdef"
        for _ in range(1000):
            random_hex = utilities.random_string(5, chars=hex_chars)
            for char in random_hex:
                self.assertIn(char, random_hex)

    def test_format_date(self):
        timestamp = datetime(2010, 12, 19, 20, 5, 30)
        formatted = utilities.format_date("dd/MM/yyyy HH:mm:ss", timestamp)
        self.assertEqual("19/12/2010 20:05:30", formatted)

    def test_format_date_epoch(self):
        timestamp = datetime.fromtimestamp(1292789130)
        formatted = utilities.format_date(datetime_obj=timestamp)
        self.assertEqual("1292789130000", formatted)
