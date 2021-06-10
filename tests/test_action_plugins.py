import os
from unittest import TestCase
import tempfile
import shutil

from apiritif.action_plugins import PLUGINS_PATH, import_plugins, ActionHandlerFactory, BaseActionHandler


class TestRequests(TestCase):

    def setUp(self):
        # create temp python package
        self.temp_dir = tempfile.TemporaryDirectory()
        plugin_dir = os.path.join(self.temp_dir.name, 'plugins')
        os.mkdir(plugin_dir)

        # create __init__.py file
        init_file = os.path.join(plugin_dir, '__init__.py')
        open(init_file, 'a').close()

        # create plugin file
        template_path = os.path.join(os.path.dirname(__file__), "resources", "action_plugin_template.txt")
        action_plugin = os.path.join(plugin_dir, 'bzm_logger.py')
        shutil.copyfile(template_path, action_plugin)

        # add path to env vars
        os.environ[PLUGINS_PATH] = plugin_dir

    def tearDown(self):
        if os.environ.get(PLUGINS_PATH):
            del os.environ[PLUGINS_PATH]

    def test_flow(self):
        import_plugins()
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
