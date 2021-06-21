import os
import sys
from abc import ABCMeta, abstractmethod
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from apiritif.utils import log

PLUGINS_PATH = 'PLUGINS_PATH'


def import_plugins():
    path = os.environ.get(PLUGINS_PATH, None)
    if not path:
        log.debug('Plugins PATH not found, continue without plugins')
        return

    # add plugins path to PYTHONPATH
    sys.path.append(path)

    package = Path(path).resolve().name
    log.info(f'Plugins package {package}')

    #  modules listing in the root package
    for (_, module_name, _) in iter_modules([path]):
        log.info(f'Importing module {module_name}')
        import_module(module_name)


class BaseActionHandler(metaclass=ABCMeta):

    YAML_ACTION_START = 'yaml_action_start'
    YAML_ACTION_END = 'yaml_action_end'
    TEST_CASE_START = 'test_case_start'
    TEST_CASE_STOP = 'test_case_stop'

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def startup(self):
        pass

    @abstractmethod
    def handle(self, session_id, action_type, action):
        pass

    @abstractmethod
    def finalize(self):
        pass


class ActionHandlerFactory:
    registry = {}

    @classmethod
    def register(cls, name):
        def inner_wrapper(wrapped_class):
            cls.registry[name] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def create_handler(cls, name, **kwargs):
        if name not in cls.registry:
            log.warning('Handler %s does not exist in the registry', name)
            return

        exec_class = cls.registry[name]
        return exec_class(**kwargs)

    @classmethod
    def create_all(cls, **kwargs):
        return [cls.create_handler(name, **kwargs) for name in cls.registry]
