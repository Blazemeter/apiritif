import copy
import logging
import os
import tempfile

import apiritif
from apiritif import store, context
from apiritif.loadgen import Worker, Params, Supervisor, JTLSampleWriter
from tests.testcases import AsyncTestCase

dummy_tests = [os.path.join(os.path.dirname(__file__), "resources", "test_dummy.py")]

logging.basicConfig(level=logging.DEBUG)


class DummyWriter(JTLSampleWriter):
    def __init__(self, output_file, workers_log):
        super(DummyWriter, self).__init__(output_file)
        with open(workers_log, 'a') as log:
            log.write("%s\n" % os.getpid())


class TestLoadGen(AsyncTestCase):
    def setUp(self):
        self.required_method_called = False
        super(TestLoadGen, self).setUp()

    def get_required_method_async(self, method):
        async def required_method(*args, **kwargs):
            self.required_method_called = True
            await method(*args, **kwargs)
        return required_method

    def test_thread(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        params = Params()
        params.concurrency = 2
        params.iterations = 10
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        self.run_until_complete(worker)

    def test_setup_errors(self):
        error_tests = [os.path.join(os.path.dirname(__file__), "resources", "test_setup_errors.py")]

        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        params = Params()
        params.concurrency = 1
        params.iterations = 1
        params.report = outfile.name
        params.tests = error_tests
        params.verbose = True

        worker = Worker(params)
        self.assertRaises(RuntimeError, self.run_until_complete, worker)

        with open(outfile.name, 'rt') as _file:
            _file.read()

    def test_worker(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        params = Params()
        params.concurrency = 2
        params.iterations = 10
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        self.run_until_complete(worker)

    def test_empty_worker(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)
        params = Params()
        params.concurrency = 2
        params.iterations = 10
        params.report = outfile.name
        params.tests = []

        worker = Worker(params)
        self.assertRaises(RuntimeError, self.run_until_complete, worker)

    def test_supervisor(self):
        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.tests = dummy_tests
        params.report = outfile.name
        params.concurrency = 9
        params.iterations = 5

        supervisor = Supervisor(params)
        self.run_until_complete(supervisor)

    def test_empty_supervisor(self):
        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.tests = []
        params.report = outfile.name
        params.concurrency = 9
        params.iterations = 5

        supervisor = Supervisor(params)
        original_finish = supervisor.finish
        supervisor.finish = self.get_required_method_async(supervisor.finish)   # check whether close has been called

        self.assertRaises(RuntimeError, self.run_until_complete, supervisor)
        self.assertTrue(self.required_method_called)
        for worker in supervisor.workers:
            self.assertTrue(worker.done())

        supervisor.finish = original_finish

    def test_writers_x3(self):
        # writers must:
        #   1. be the same for threads of one process
        #   2. be set up only once
        #   3. be different for different processes
        def dummy_supervisor_init(self, params):
            """
            :type params: Params
            """
            self.params = params
            store.writer = DummyWriter(self.params.report, self.params.workers_log)

            super(Supervisor, self).__init__(coro=self._start_workers())

        outfile = tempfile.NamedTemporaryFile()
        outfile.close()

        params = Params()

        # use this log to spy on writers
        workers_log = outfile.name + '-workers.log'
        params.workers_log = workers_log

        params.tests = [os.path.join(os.path.dirname(__file__), "resources", "test_smart_transactions.py")]
        params.report = outfile.name

        # it causes 3 workers totally
        params.concurrency = 3

        params.iterations = 2
        saved_supervisor_init = Supervisor.__init__
        Supervisor.__init__ = dummy_supervisor_init
        try:
            supervisor = Supervisor(params)
            self.run_until_complete(supervisor)

            with open(workers_log) as log:
                writers = log.readlines()
            self.assertEqual(1, len(writers))
        finally:
            Supervisor.__init__ = saved_supervisor_init

            os.remove(workers_log)
            os.remove(params.report)

    def test_handlers(self):
        # handlers must:
        #   1. be unique for thread
        #   2. be set up every launch of test suite
        def log_line(line):
            with open(context.handlers_log, 'a') as log:
                log.write("%s\n" % line)

        saved_get_handlers = apiritif.get_transaction_handlers
        saved_set_handlers = apiritif.set_transaction_handlers

        def mock_get_handlers():
            transaction_handlers = saved_get_handlers()
            if not transaction_handlers:
                transaction_handlers = {'enter': [], 'exit': []}

            length = "%s/%s" % (len(transaction_handlers['enter']), len(transaction_handlers['exit']))
            log_line("get: {pid: %s, idx: %s, iteration: %s, len: %s}" %
                     (os.getpid(), context.get_index(), context.get_iteration(), length))
            return transaction_handlers

        def mock_set_handlers(handlers):
            log_line("set: {pid: %s, idx: %s, iteration: %s, handlers: %s}," %
                     (os.getpid(), context.get_index(), context.get_iteration(), handlers))
            saved_set_handlers(handlers)

        outfile = tempfile.NamedTemporaryFile()
        outfile.close()

        params = Params()

        # use this log to spy on writers
        handlers_log = outfile.name + '-handlers.log'
        context.handlers_log = handlers_log

        params.tests = [os.path.join(os.path.dirname(__file__), "resources", "test_smart_transactions.py")]
        params.report = outfile.name

        # it causes 2 processes and 3 threads (totally)
        params.concurrency = 3
        params.worker_count = 2

        params.iterations = 2
        apiritif.get_transaction_handlers = mock_get_handlers
        apiritif.set_transaction_handlers = mock_set_handlers
        try:
            supervisor = Supervisor(params)
            self.run_until_complete(supervisor)

            with open(handlers_log) as log:
                handlers = log.readlines()

            self.assertEqual(36, len(handlers))
            self.assertEqual(6, len([handler for handler in handlers if handler.startswith('set')]))
            self.assertEqual(0, len([handler for handler in handlers if handler.endswith('2/2}')]))

        finally:
            apiritif.get_transaction_handlers = saved_get_handlers
            apiritif.set_transaction_handlers = saved_set_handlers

            os.remove(handlers_log)
            os.remove(outfile.name)

    def test_ramp_up1(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)

        params1 = Params()
        params1.concurrency = 50
        params1.report = outfile.name
        params1.tests = dummy_tests
        params1.ramp_up = 60
        params1.steps = 5

        params1.worker_index = 0

        supervisor1 = Supervisor(params1)
        res1 = [x.delay for x in supervisor1._get_worker_params()]
        print(res1)
        self.assertEquals(params1.concurrency, len(res1))

        params2 = copy.deepcopy(params1)
        params2.worker_index = 1
        supervisor2 = Supervisor(params2)
        res2 = [x.delay for x in supervisor2._get_worker_params()]
        print(res2)
        self.assertEquals(params2.concurrency, len(res2))

        print(sorted(res1 + res2))

    def test_ramp_up2(self):
        outfile = tempfile.NamedTemporaryFile()
        print(outfile.name)

        params1 = Params()
        params1.concurrency = 50
        params1.report = outfile.name
        params1.tests = dummy_tests
        params1.ramp_up = 60

        params1.worker_index = 0

        supervisor1 = Supervisor(params1)
        res1 = [x.delay for x in supervisor1._get_worker_params()]
        print(res1)
        self.assertEquals(params1.concurrency, len(res1))

    def test_unicode_ldjson(self):
        outfile = tempfile.NamedTemporaryFile(suffix=".ldjson")
        print(outfile.name)
        params = Params()
        params.concurrency = 2
        params.iterations = 1
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        self.run_until_complete(worker)

        with open(outfile.name) as fds:
            print(fds.read())
