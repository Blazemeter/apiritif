import json
import tempfile
from collections import namedtuple
from unittest import TestCase

from _pytest.config import PytestPluginManager
from _pytest.config.argparsing import Parser
from _pytest.nodes import Node

import apiritif
from apiritif import http
from apiritif.pytest_plugin import pytest_addoption, pytest_configure, pytest_unconfigure, ApiritifPytestPlugin

ctype = namedtuple("config", ["option", "pluginmanager"])
otype = namedtuple("option", ["apiritif_trace", "apiritif_trace_detail"])


class TestHTTPMethods(TestCase):
    def test_addoption(self):
        parser = Parser()
        pytest_addoption(parser)

    def test_configure_none(self):
        config = ctype(otype(None, 1), PytestPluginManager())
        pytest_configure(config)
        pytest_unconfigure(config)

    def test_configure_some(self):
        config = ctype(otype("somefile", 1), PytestPluginManager())
        pytest_configure(config)
        pytest_unconfigure(config)

    def test_flow_mindetail(self):
        tmp = tempfile.NamedTemporaryFile()
        tmp.close()
        config = ctype(otype(tmp.name, 1), PytestPluginManager())
        plugin = ApiritifPytestPlugin(config)
        for _ in plugin.pytest_runtest_setup(None):
            pass

        with apiritif.transaction("tran"):
            pass

        node = Node("test", nodeid="tst", config=config, session="some")
        for _ in plugin.pytest_runtest_teardown(node):
            pass

        plugin.pytest_sessionfinish(None)

        with open(tmp.name) as fp:
            data = json.load(fp)

        self.assertNotEqual({}, data)

    def test_flow_maxdetail(self):
        tmp = tempfile.NamedTemporaryFile()
        tmp.close()
        config = ctype(otype(tmp.name, 4), PytestPluginManager())
        plugin = ApiritifPytestPlugin(config)
        for _ in plugin.pytest_runtest_setup(None):
            pass

        with apiritif.transaction("tran") as tran:
            tran.set_request(bytes("test", 'utf8'))

        http.post('http://httpbin.org/post', data=bytes([0xa0, 1, 2, 3]),
                  headers={'Content-Type': 'application/octet-stream'})

        node = Node("test", nodeid="tst", config=config, session="some")
        for _ in plugin.pytest_runtest_teardown(node):
            pass

        plugin.pytest_sessionfinish(None)

        with open(tmp.name) as fp:
            data = json.load(fp)

        self.assertNotEqual({}, data)
