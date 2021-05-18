from abc import ABCMeta, abstractmethod
from importlib import import_module
from inspect import isclass
from pathlib import Path
from pkgutil import iter_modules

from ..utils import log


def import_plugins():
    root_path = Path(__file__).resolve().parent
    for (_, module_name, _) in iter_modules([root_path]):
        module = import_module(f"{__name__}.{module_name}")
        for class_name in dir(module):
            module_subclass = getattr(module, class_name)
            if isclass(module_subclass) and issubclass(module_subclass, BaseActionHandler):
                log.info(f'Apiritif plugin found: {class_name}')
                globals()[class_name] = module_subclass


class BaseActionHandler(metaclass=ABCMeta):

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def startup(self):
        pass

    @abstractmethod
    def log(self, log_line):
        pass

    @abstractmethod
    def finalize(self):
        pass


class ActionHandlerFactory:

    registry = {}

    @classmethod
    def reg(cls, name, wrapped_class):
        cls.registry[name] = wrapped_class

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
            return None

        exec_class = cls.registry[name]
        return exec_class(**kwargs)

    @classmethod
    def create_all(cls, **kwargs):
        return [cls.create_handler(name, **kwargs) for name in cls.registry.keys()]
