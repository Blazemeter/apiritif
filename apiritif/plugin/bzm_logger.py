from apiritif.plugin import BaseActionHandler, ActionHandlerFactory


@ActionHandlerFactory.register('local')
class BZMActionHandler(BaseActionHandler):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        ActionHandlerFactory.reg('local', self.__class__)

    def startup(self):
        pass

    def finalize(self):
        pass

    def log(self, log_line: str):
        print(f'BZM: {log_line}')
