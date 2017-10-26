import os
import tempfile
from unittest import TestCase

from apiritif.loadgen import Worker


class TestLoadGen(TestCase):
    def test_worker(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        worker = Worker(1, outfile.name, [os.path.join(os.path.dirname(__file__), "test_dummy.py")], 2)
        worker.start()
        worker.join()
        os.remove(outfile.name)
