import copy
import logging
import os
import tempfile
import time
import threading
from unittest import TestCase
from multiprocessing.pool import CLOSE

import apiritif
from apiritif import store, thread
from apiritif.samples import Sample
from apiritif.loadgen import Worker, Params, Supervisor, JTLSampleWriter

dummy_tests = [os.path.join(os.path.dirname(__file__), "resources", "test_dummy.py")]
logging.basicConfig(level=logging.DEBUG)


class DummyWriter(JTLSampleWriter):
    def __init__(self, output_file, workers_log):
        super(DummyWriter, self).__init__(output_file)
        with open(workers_log, 'a') as log:
            log.write("%s\n" % os.getpid())


class TestLoadGen(TestCase):
    def setUp(self):
        self.required_method_called = False

    def get_required_method(self, method):
        def required_method(*args, **kwargs):
            self.required_method_called = True
            method(*args, **kwargs)
        return required_method

    def test_thread(self):
        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.concurrency = 2
        params.iterations = 10
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        worker.run_nose(params)

    def test_setup_errors(self):
        error_tests = [os.path.join(os.path.dirname(__file__), "resources", "test_setup_errors.py")]

        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.concurrency = 1
        params.iterations = 1
        params.report = outfile.name
        params.tests = error_tests
        params.verbose = True

        worker = Worker(params)
        self.assertRaises(RuntimeError, worker.run_nose, params)

        with open(outfile.name, 'rt') as _file:
            _file.read()

    def test_worker(self):
        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.concurrency = 2
        params.iterations = 10
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        worker.start()
        worker.join()

    def test_empty_worker(self):
        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.concurrency = 2
        params.iterations = 10
        params.report = outfile.name
        params.tests = []

        worker = Worker(params)
        worker.close = self.get_required_method(worker.close)   # check whether close has been called
        try:
            worker.start()
        except:     # assertRaises doesn't catch it
            pass
        self.assertTrue(self.required_method_called)

    def test_supervisor(self):
        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.tests = dummy_tests
        params.report = outfile.name + "%s"
        params.concurrency = 9
        params.iterations = 5
        sup = Supervisor(params)
        sup.start()
        while sup.isAlive():
            time.sleep(1)

    def test_empty_supervisor(self):
        outfile = tempfile.NamedTemporaryFile()
        params = Params()
        params.tests = []
        params.report = outfile.name + "%s"
        params.concurrency = 9
        params.iterations = 5
        sup = Supervisor(params)
        sup.start()
        while sup.isAlive():
            time.sleep(1)

        self.assertEqual(CLOSE, sup.workers._state)

    def test_handlers(self):
        # handlers must:
        #   1. be unique for thread
        #   2. be set up every launch of test suite
        def log_line(line):
            with open(thread.handlers_log, 'a') as log:
                log.write("%s\n" % line)

        def mock_get_handlers():
            transaction_handlers = thread.get_from_thread_store('transaction_handlers')
            if not transaction_handlers:
                transaction_handlers = {'enter': [], 'exit': []}

            length = "%s/%s" % (len(transaction_handlers['enter']), len(transaction_handlers['exit']))
            log_line("get: {pid: %s, idx: %s, iteration: %s, len: %s}" %
                     (os.getpid(), thread.get_index(), thread.get_iteration(), length))
            return transaction_handlers

        def mock_set_handlers(handlers):
            log_line("set: {pid: %s, idx: %s, iteration: %s, handlers: %s}," %
                     (os.getpid(), thread.get_index(), thread.get_iteration(), handlers))
            thread.put_into_thread_store(transaction_handlers=handlers)

        outfile = tempfile.NamedTemporaryFile()
        outfile.close()

        params = Params()

        # use this log to spy on writers
        handlers_log = outfile.name + '-handlers.log'
        thread.handlers_log = handlers_log

        params.tests = [os.path.join(os.path.dirname(__file__), "resources", "test_smart_transactions.py")]
        params.report = outfile.name + "%s"

        # it causes 2 processes and 3 threads (totally)
        params.concurrency = 3
        params.worker_count = 2

        params.iterations = 2
        saved_get_handlers = apiritif.get_transaction_handlers
        saved_set_handlers = apiritif.set_transaction_handlers
        apiritif.get_transaction_handlers = mock_get_handlers
        apiritif.set_transaction_handlers = mock_set_handlers
        try:
            sup = Supervisor(params)
            sup.start()
            while sup.isAlive():
                time.sleep(1)

            with open(handlers_log) as log:
                handlers = log.readlines()

            self.assertEqual(36, len(handlers))
            self.assertEqual(6, len([handler for handler in handlers if handler.startswith('set')]))
            self.assertEqual(0, len([handler for handler in handlers if handler.endswith('2/2}')]))

        finally:
            apiritif.get_transaction_handlers = saved_get_handlers
            apiritif.set_transaction_handlers = saved_set_handlers

            os.remove(handlers_log)
            for i in range(params.worker_count):
                os.remove(params.report % i)

    def test_ramp_up1(self):
        outfile = tempfile.NamedTemporaryFile()

        params1 = Params()
        params1.concurrency = 50
        params1.report = outfile.name
        params1.tests = dummy_tests
        params1.ramp_up = 60
        params1.steps = 5

        params1.worker_count = 2
        params1.worker_index = 0

        worker1 = Worker(params1)
        res1 = [x.delay for x in worker1._get_thread_params()]
        self.assertEquals(params1.concurrency, len(res1))

        params2 = copy.deepcopy(params1)
        params2.worker_index = 1
        worker2 = Worker(params2)
        res2 = [x.delay for x in worker2._get_thread_params()]
        self.assertEquals(params2.concurrency, len(res2))

    def test_ramp_up2(self):
        outfile = tempfile.NamedTemporaryFile()

        params1 = Params()
        params1.concurrency = 50
        params1.report = outfile.name
        params1.tests = dummy_tests
        params1.ramp_up = 60

        params1.worker_count = 1
        params1.worker_index = 0

        worker1 = Worker(params1)
        res1 = [x.delay for x in worker1._get_thread_params()]
        self.assertEquals(params1.concurrency, len(res1))

    def test_unicode_ldjson(self):
        outfile = tempfile.NamedTemporaryFile(suffix=".ldjson")
        params = Params()
        params.concurrency = 2
        params.iterations = 1
        params.report = outfile.name
        params.tests = dummy_tests

        worker = Worker(params)
        worker.start()
        worker.join()

        with open(outfile.name) as fds:
            result = fds.readlines()
        self.assertEqual(4, len(result))


class SampleGenerator(threading.Thread):
    def __init__(self, writer, index, outfile_name):
        super(SampleGenerator, self).__init__(target=self._write_sample)
        self.writer = writer
        self.index = index
        self.outfile_name = outfile_name
        self.sample = Sample(start_time=index, duration=index, test_case="Generator %s" % index)

    def _write_sample(self):
        self.writer.add(self.sample, self.index, self.index)
        time.sleep(0.2)

        with open(self.outfile_name) as log:
            self.written_results = log.readlines()


class TestWriter(TestCase):

    # Writer have to write results while application is running.
    # Here some fake threads (SampleGenerator) send `Sample` on writing.
    # Then after a delay we exposing data from the result file and verify there is something already written.
    def test_writer_works_in_background(self):
        outfile = tempfile.NamedTemporaryFile()
        outfile.close()

        writer = JTLSampleWriter(outfile.name)
        sample_generators = [SampleGenerator(writer, i, outfile.name) for i in range(5)]

        with writer:
            for generator in sample_generators:
                generator.start()
            for generator in sample_generators:
                generator.join()

        while not writer.is_queue_empty() and writer.is_alive():
            time.sleep(0.1)

        for generator in sample_generators:
            self.assertTrue(len(generator.written_results) > 1)

    def test_writers_x3(self):
        # writers must:
        #   1. be the same for threads of one process
        #   2. be set up only once
        #   3. be different for different processes
        def dummy_worker_init(self, params):
            """
            :type params: Params
            """
            super(Worker, self).__init__(params.concurrency)
            self.params = params
            store.writer = DummyWriter(self.params.report, self.params.workers_log)

        outfile = tempfile.NamedTemporaryFile()
        outfile.close()

        params = Params()

        # use this log to spy on writers
        workers_log = outfile.name + '-workers.log'
        params.workers_log = workers_log

        params.tests = [os.path.join(os.path.dirname(__file__), "resources", "test_smart_transactions.py")]
        params.report = outfile.name + "%s"

        # it causes 2 processes and 3 threads (totally)
        params.concurrency = 3
        params.worker_count = 2

        params.iterations = 2
        saved_worker_init = Worker.__init__
        Worker.__init__ = dummy_worker_init
        try:
            sup = Supervisor(params)
            sup.start()
            while sup.isAlive():
                time.sleep(1)

            with open(workers_log) as log:
                writers = log.readlines()
            self.assertEqual(2, len(writers))
            self.assertNotEqual(writers[0], writers[1])
        finally:
            Worker.__init__ = saved_worker_init

            os.remove(workers_log)
            for i in range(params.worker_count):
                os.remove(params.report % i)


def mock_spawn_worker(params):
    with open(params.report, 'w') as log:
        log.write(str(os.getpid()))
        time.sleep(0.2)


class TestMultiprocessing(TestCase):

    # Each worker should be spawned in separate process
    # Replace new process function `spawn_worker` with `mock_spawn_worker`
    # This mock function writes in process report file pid of the process
    # Test collect data from all report files and verify different ids count.
    def test_worker_spawned_as_separate_process(self):
        outfile = tempfile.NamedTemporaryFile()
        outfile.close()

        params = Params()
        params.report = outfile.name + "%s"
        params.concurrency = 15
        params.worker_count = 15

        params.iterations = 1
        saved_spawn_worker = apiritif.loadgen.spawn_worker
        apiritif.loadgen.spawn_worker = mock_spawn_worker

        try:
            sup = Supervisor(params)
            sup.start()
            while sup.isAlive():
                time.sleep(0.1)

            process_ids = []
            for i in range(params.worker_count):
                with open(params.report % i) as f:
                    process_ids.extend(f.readlines())
            self.assertEqual(params.worker_count, len(set(process_ids)))

        finally:
            apiritif.loadgen.spawn_worker = saved_spawn_worker

            for i in range(params.worker_count):
                os.remove(params.report % i)
