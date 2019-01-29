import hashlib
import os
import threading
import unittest

from apiritif.feeders import CSVFeeder


class TestSimple(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(TestSimple, self).__init__(methodName)
        self.feeder = CSVFeeder.per_thread(os.path.join(os.path.dirname(__file__), "data/source.csv"))
        self.feeder.read_vars()

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        self.vars = self.feeder.get_vars()

    def test_first(self):
        print("!!%s!!" % self.feeder.get_vars())
        pass
        # with apiritif.transaction('http://blazedemo.com/{}/{}'.format(vars['name'], vars['pass'])):
        # response = apiritif.http.get('http://blazedemo.com/{}/{}'.format(vars['name'], vars['pass']))

    def test_second(self):
        with open("/tmp/apiritif.log", "a") as _file:
            pid = str(os.getpid())
            tid = str(threading.current_thread().ident)
            hid = hashlib.md5()
            hid.update(pid.encode())
            hid.update(tid.encode())
            log_line = "%s. %s:%s {%s:%s}\n" % (
                hid.hexdigest()[:3], pid[-3:], tid[-3:], self.vars["name"], self.vars["pass"])
            print(log_line)
            _file.write(log_line)
