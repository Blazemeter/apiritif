import asyncio

from unittest import TestCase
from apiritif import thread


class AsyncTestCase(TestCase):
    def setUp(self):
        self.base_loop = asyncio.get_event_loop()
        self.base_context_vars = thread.context_variables

        self.test_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.test_loop)
        thread.context_variables = thread.ContextVariables()

    def tearDown(self):
        asyncio.set_event_loop(self.base_loop)
        thread.context_variables = self.base_context_vars
        self.test_loop.close()

    def run_until_complete(self, awaitable):
        loop = asyncio.get_event_loop()
        if type(awaitable) is list:
            awaitable = asyncio.gather(*awaitable)

        return loop.run_until_complete(awaitable)
