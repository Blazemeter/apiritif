import hashlib
import os
import threading
import unittest

from apiritif.feeders import CSVFeeder

feeder = CSVFeeder.per_thread(os.path.join(os.path.dirname(__file__), "data/source.csv"))

class TestSimple(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        feeder.read_vars()

    def setUp(self):
        self.vars = feeder.get_vars()

    def test_first(self):
        print("%s!!%s!!" % (id(feeder), feeder.get_vars()))
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