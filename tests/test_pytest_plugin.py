import json
import tempfile
from collections import namedtuple
from unittest import TestCase

from _pytest.config import PytestPluginManager
from _pytest.config.argparsing import Parser
from _pytest.nodes import Node

import apiritif
from apiritif.pytest_plugin import pytest_addoption, pytest_configure, pytest_unconfigure, ApiritifPlugin

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

    def test_flow(self):
        tmp = tempfile.NamedTemporaryFile()
        tmp.close()
        config = ctype(otype(tmp.name, 1), PytestPluginManager())
        plugin = ApiritifPlugin(config)
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
