import json
import tempfile
from collections import namedtuple
from contextlib import contextmanager
from unittest import TestCase

from _pytest.config import PytestPluginManager
from _pytest.config.argparsing import Parser
from _pytest.nodes import Node
from _pytest.reports import TestReport
from _pytest.runner import CallInfo
from pluggy.callers import _Result

import apiritif
from apiritif import http
from apiritif.pytest_plugin import pytest_addoption, pytest_configure, pytest_unconfigure, ApiritifPytestPlugin

ctype = namedtuple("config", ["option", "pluginmanager", "getoption"])
otype = namedtuple("option", ["apiritif_trace", "apiritif_trace_detail"])


@contextmanager
def fake_process(trace_fname):
    config = ctype(otype(trace_fname, 4), PytestPluginManager(), lambda x, y: 0)
    plugin = ApiritifPytestPlugin(config)
    next(plugin.pytest_runtest_setup(None))

    yield

    node = Node("test", nodeid="tst", config=config, session="some")
    node._report_sections = []
    node.location = []
    node.user_properties = []
    call = CallInfo.from_call(lambda: 1, 'call')
    report = TestReport.from_item_and_call(node, call)
    result = _Result(report, None)
    gen = plugin.pytest_runtest_makereport(node, call)
    next(gen)
    try:
        gen.send(result)
    except StopIteration:
        pass

    plugin.pytest_sessionfinish(None)


class TestHTTPMethods(TestCase):
    def test_addoption(self):
        parser = Parser()
        pytest_addoption(parser)

    def test_configure_none(self):
        config = ctype(otype(None, 1), PytestPluginManager(), lambda x, y: 0)
        pytest_configure(config)
        pytest_unconfigure(config)

    def test_configure_some(self):
        config = ctype(otype("somefile", 1), PytestPluginManager(), lambda x, y: 0)
        pytest_configure(config)
        pytest_unconfigure(config)

    def test_flow_mindetail(self):
        tmp = tempfile.NamedTemporaryFile()
        tmp.close()

        with fake_process(tmp.name):
            with apiritif.transaction("tran"):
                pass

        with open(tmp.name) as fp:
            data = json.load(fp)

        self.assertNotEqual({}, data)

    def test_flow_maxdetail(self):
        tmp = tempfile.NamedTemporaryFile()
        tmp.close()

        with fake_process(tmp.name):
            with apiritif.transaction("tran") as tran:
                tran.set_request(bytes("test", 'utf8'))

            http.post('http://httpbin.org/post', data=bytes([0xa0, 1, 2, 3]),
                      headers={'Content-Type': 'application/octet-stream'})

        with open(tmp.name) as fp:
            data = json.load(fp)

        self.assertNotEqual({}, data)
