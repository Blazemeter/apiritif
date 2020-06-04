import json
import sys

import pytest

import apiritif
from apiritif.samples import ApiritifSampleExtractor, Sample


def pytest_addoption(parser):
    group = parser.getgroup('apiritif', 'reporting per-testcase Apiritif traces')
    group.addoption('--apiritif-trace', help='target path to save trace JSON')
    group.addoption('--apiritif-trace-detail', type=int, default=1, help='detail level for Apiritif trace (1-3)')


def pytest_configure(config):
    if not config.option.apiritif_trace:
        return
    plugin = ApiritifPytestPlugin(config)
    config.pluginmanager.register(plugin, plugin.__class__.__name__)


def pytest_unconfigure(config):
    name = ApiritifPytestPlugin.__name__
    if config.pluginmanager.has_plugin(name):
        plugin = config.pluginmanager.get_plugin(name)
        config.pluginmanager.unregister(plugin)


class ApiritifPytestPlugin(object):
    def __init__(self, config=None) -> None:
        super().__init__()
        self._result_file = None
        self._detail_level = 1
        if config:
            self._result_file = config.option.apiritif_trace
            self._detail_level = config.option.apiritif_trace_detail
        self._trace_map = {}

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        self._pop_events()  # clean it, just in case
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item):
        self._trace_map[item.nodeid] = self._get_subsamples()
        yield

    def _get_subsamples(self):
        recording = self._pop_events()
        sample = Sample()
        extr = ApiritifSampleExtractor()
        trace = extr.parse_recording(recording, sample)
        toplevel_sample = trace[0].to_dict()
        self._filter([toplevel_sample])
        return toplevel_sample

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session):
        with open(self._result_file, 'w') as fp:
            json.dump(self._trace_map, fp, indent=True)

    def _pop_events(self):
        return apiritif.recorder.pop_events(from_ts=-1, to_ts=sys.maxsize)

    def _filter(self, items):
        for item in items:
            self._filter(item['subsamples'])
            if self._detail_level >= 4:
                if isinstance(item['extras'].get('requestBody'), bytes):
                    item['extras']['requestBody'] = item['extras']['requestBody'].decode('utf-8')

            if self._detail_level <= 3:
                item['extras'].pop('requestCookiesRaw', None)
                item['extras'].pop('requestCookies', None)
                item['extras'].pop('requestBody', None)
                item['extras'].pop('responseBody', None)
                item['extras'].pop('requestHeaders', None)
                item['extras'].pop('responseHeaders', None)

            if self._detail_level <= 2:
                item.pop('extras', None)
                item.pop('subsamples', None)
                item.pop('assertions', None)
