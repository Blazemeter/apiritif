import os
from unittest import TestCase
import tempfile
import shutil

import apiritif
from apiritif import thread

from apiritif.action_plugins import PLUGINS_PATH, import_plugins, ActionHandlerFactory, BaseActionHandler
from apiritif.loadgen import Worker, Params
from tests.unit import RESOURCES_DIR
from tests.unit.test_loadgen import dummy_tests


class TestRequests(TestCase):

    def setUp(self):
        # create temp python package
        self.temp_dir = tempfile.TemporaryDirectory()
        plugin_dir = os.path.join(self.temp_dir.name, 'plugins')
        os.mkdir(plugin_dir)

        # create __init__.py file
        init_file = os.path.join(plugin_dir, '../__init__.py')
        open(init_file, 'a').close()

        # create plugin file
        template_path = os.path.join(RESOURCES_DIR, "action_plugin_template.txt")
        action_plugin = os.path.join(plugin_dir, 'bzm_logger.py')
        shutil.copyfile(template_path, action_plugin)

        # add path to env vars
        os.environ[PLUGINS_PATH] = plugin_dir
        import_plugins()

    def tearDown(self):
        if os.environ.get(PLUGINS_PATH):
            del os.environ[PLUGINS_PATH]

    def test_flow(self):
        plugins = ActionHandlerFactory.create_all()
        self.assertEquals(1, len(plugins))
        plugin = plugins.pop(0)
        plugin.startup()
        plugin.handle('session_id', BaseActionHandler.YAML_ACTION_START, 'data')
        plugin.finalize()

        self.assertTrue(plugin.started)
        self.assertTrue(plugin.ended)
        self.assertEquals(
            ('session_id', BaseActionHandler.YAML_ACTION_START, 'data'),
            plugin.actions.pop()
        )

    def test_external_handler(self):
        plugins = ActionHandlerFactory.create_all()
        apiritif.put_into_thread_store(action_handlers=plugins)
        apiritif.external_handler('session_id', BaseActionHandler.YAML_ACTION_START, 'data')
        plugin = plugins.pop(0)
        self.assertEquals(
            ('session_id', BaseActionHandler.YAML_ACTION_START, 'data'),
            plugin.actions.pop()
        )

    def test_loadgen(self):
        params = Params()
        params.iterations = 1
        params.concurrency = 1
        params.report = 'log.ldjson'
        params.tests = dummy_tests
        worker = Worker(params)
        worker.run_nose(params)
        action_handlers = thread.get_from_thread_store('action_handlers')
        plugin = action_handlers.pop(0)
        self.assertTrue(plugin.started)
        self.assertTrue(plugin.ended)
