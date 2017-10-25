import os
from unittest import TestCase

from apiritif.loadgen import Worker


class TestLoadGen(TestCase):
    def test_worker(self):
        worker = Worker(1, "afile", [os.path.join(os.path.dirname(__file__), "test_dummy.py")], 2)
        worker.start()
        worker.join()
