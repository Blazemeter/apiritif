"""

Copyright 2017 BlazeMeter Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import copy
import unicodecsv as csv
import json
import logging
import multiprocessing
import os
import sys
import time
import traceback
from multiprocessing.pool import ThreadPool
from optparse import OptionParser
from threading import Thread

from nose2.main import PluggableTestProgram
from nose2.events import Plugin

import apiritif
import apiritif.thread as thread
import apiritif.store as store
from apiritif.action_plugins import ActionHandlerFactory, import_plugins
from apiritif.utils import NormalShutdown, log, get_trace, VERSION, graceful


# TODO how to implement hits/s control/shape?
# TODO: VU ID for script
# TODO: disable assertions for load mode


def spawn_worker(params):
    """
    This method has to be module level function

    :type params: Params
    """
    setup_logging(params)
    log.info("Adding worker: idx=%s\tconcurrency=%s\tresults=%s", params.worker_index, params.concurrency,
             params.report)
    worker = Worker(params)
    worker.start()
    worker.join()


class Params(object):
    def __init__(self):
        super(Params, self).__init__()
        self.worker_index = 0
        self.worker_count = 1
        self.thread_index = 0
        self.report = None

        self.delay = 0

        self.concurrency = 1
        self.iterations = 1
        self.ramp_up = 0
        self.steps = 0
        self.hold_for = 0

        self.verbose = False

        self.tests = None

    def __repr__(self):
        return "%s" % self.__dict__


class Supervisor(Thread):
    """
    apiritif-loadgen CLI utility
        overwatch workers, kill them when terminated
        probably reports through stdout log the names of report files
    :type params: Params
    """

    def __init__(self, params):
        super(Supervisor, self).__init__(target=self._start_workers)
        self.daemon = True
        self.name = self.__class__.__name__

        self.params = params
        self.workers = None

    def _concurrency_slicer(self, ):
        total_concurrency = 0
        inc = self.params.concurrency / float(self.params.worker_count)
        assert inc >= 1
        for idx in range(0, self.params.worker_count):
            progress = (idx + 1) * inc

            conc = int(round(progress - total_concurrency))
            assert conc > 0

            log.debug("Idx: %s, concurrency: %s", idx, conc)

            params = copy.deepcopy(self.params)
            params.worker_index = idx
            params.thread_index = total_concurrency  # for subprocess it's index of its first thread
            params.concurrency = conc
            params.report = self.params.report % idx
            params.worker_count = self.params.worker_count

            total_concurrency += conc

            yield params

        assert total_concurrency == self.params.concurrency

    def _start_workers(self):
        log.info("Total workers: %s", self.params.worker_count)

        thread.set_total(self.params.concurrency)
        self.workers = multiprocessing.Pool(processes=self.params.worker_count)
        args = list(self._concurrency_slicer())

        try:
            self.workers.map(spawn_worker, args)
        finally:
            self.workers.close()
            self.workers.join()
        # TODO: watch the total test duration, if set, 'cause iteration might last very long


class ApiritifSession(PluggableTestProgram.sessionClass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_reason = ""

    def set_stop_reason(self, msg):
        if not self.stop_reason:
            self.stop_reason = msg


class Worker(ThreadPool):
    def __init__(self, params):
        """
        :type params: Params
        """
        super(Worker, self).__init__(params.concurrency)
        self.params = params
        if self.params.report.lower().endswith(".ldjson"):
            store.writer = LDJSONSampleWriter(self.params.report)
        else:
            store.writer = JTLSampleWriter(self.params.report)

    def start(self):
        import_plugins()
        params = list(self._get_thread_params())
        with store.writer:  # writer must be closed finally
            try:
                self.map(self.run_nose, params)
            finally:
                self.close()

    def close(self):
        log.info("Workers finished, awaiting result writer")
        while not store.writer.is_queue_empty() and store.writer.is_alive():
            time.sleep(0.1)
        log.info("Results written, shutting down")
        super(Worker, self).close()

    def run_nose(self, params):
        """
        :type params: Params
        """
        if not params.tests:
            raise RuntimeError("Nothing to test.")

        thread.set_index(params.thread_index)
        log.debug("[%s] Starting nose2 iterations: %s", params.worker_index, params)
        assert isinstance(params.tests, list)
        # argv.extend(['--with-apiritif', '--nocapture', '--exe', '--nologcapture'])

        end_time = self.params.ramp_up + self.params.hold_for
        end_time += time.time() if end_time else 0
        time.sleep(params.delay)
        store.writer.concurrency += 1

        config = {"tests": params.tests}
        if params.verbose:
            config["verbosity"] = 3

        iteration = 0
        handlers = ActionHandlerFactory.create_all()
        log.debug(f'Action handlers created {handlers}')
        thread.put_into_thread_store(action_handlers=handlers)
        for handler in handlers:
            handler.startup()
        try:
            while not graceful():
                log.debug("Starting iteration:: index=%d,start_time=%.3f", iteration, time.time())
                thread.set_iteration(iteration)

                session = ApiritifSession()
                config["session"] = session
                ApiritifTestProgram(config=config)

                log.debug("Finishing iteration:: index=%d,end_time=%.3f", iteration, time.time())
                iteration += 1

                # reasons to stop
                if session.stop_reason:
                    if "Nothing to test." in session.stop_reason:
                        raise RuntimeError("Nothing to test.")
                    elif session.stop_reason.startswith(NormalShutdown.__name__):
                        log.info(session.stop_reason)
                    else:
                        raise RuntimeError(f"Unknown stop_reason: {session.stop_reason}")
                elif 0 < params.iterations <= iteration:
                    log.debug("[%s] iteration limit reached: %s", params.worker_index, params.iterations)
                elif 0 < end_time <= time.time():
                    log.debug("[%s] duration limit reached: %s", params.worker_index, params.hold_for)
                else:
                    continue  # continue if no one is faced

                break

        finally:
            store.writer.concurrency -= 1

            for handler in handlers:
                handler.finalize()

    def __reduce__(self):
        raise NotImplementedError()

    def _get_thread_params(self):
        if not self.params.steps or self.params.steps < 0:
            self.params.steps = sys.maxsize

        step_granularity = self.params.ramp_up / self.params.steps
        ramp_up_per_thread = self.params.ramp_up / self.params.concurrency
        for thr_idx in range(self.params.concurrency):
            offset = self.params.worker_index * ramp_up_per_thread / float(self.params.worker_count)
            delay = offset + thr_idx * float(self.params.ramp_up) / self.params.concurrency
            delay -= delay % step_granularity if step_granularity else 0
            params = copy.deepcopy(self.params)
            params.thread_index = self.params.thread_index + thr_idx
            params.delay = delay
            yield params


class ApiritifTestProgram(PluggableTestProgram):
    def __init__(self, **kwargs):
        kwargs['module'] = None
        kwargs['exit'] = False
        self.config = kwargs.pop("config")
        self.session = self.config["session"]
        self.conf_verbosity = None if "verbosity" not in self.config else self.config["verbosity"]
        super(ApiritifTestProgram, self).__init__(**kwargs)

    def parseArgs(self, argv):
        self.testLoader = self.loaderClass(self.session)
        self.session.testLoader = self.testLoader

        dir, filename = os.path.split(self.config["tests"][-1])
        self.session.startDir = dir or "."
        self.testNames = [os.path.splitext(filename)[0]]

        if self.conf_verbosity:
            self.session.verbosity = self.conf_verbosity
        self.session.verbosity = 0

        self.defaultPlugins.append("apiritif.loadgen")
        self.loadPlugins()
        self.createTests()


class LDJSONSampleWriter(object):
    """
    :type out_stream: file
    """

    def __init__(self, output_file):
        super(LDJSONSampleWriter, self).__init__()
        self.concurrency = 0
        self.output_file = output_file
        self.out_stream = None
        self._samples_queue = multiprocessing.Queue()

        self._writing = False
        self._writer_thread = Thread(target=self._writer)
        self._writer_thread.daemon = True
        self._writer_thread.name = self.__class__.__name__

    def __enter__(self):
        self.out_stream = open(self.output_file, "wb")
        self._writing = True
        self._writer_thread.start()
        return self

    def is_alive(self):
        return self._writer_thread.is_alive()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._writing = False
        self._writer_thread.join()
        self.out_stream.close()

    def add(self, sample, test_count, success_count):
        self._samples_queue.put_nowait((sample, test_count, success_count))

    def is_queue_empty(self):
        return self._samples_queue.empty()

    def _writer(self):
        while self._writing:
            if self._samples_queue.empty():
                time.sleep(0.1)

            while not self._samples_queue.empty():
                item = self._samples_queue.get(block=True)
                try:
                    sample, test_count, success_count = item
                    self._write_sample(sample, test_count, success_count)
                except BaseException as exc:
                    log.debug("Processing sample failed: %s\n%s", str(exc), traceback.format_exc())
                    log.warning("Couldn't process sample, skipping")
                    continue

    def _write_sample(self, sample, test_count, success_count):
        line = json.dumps(sample.to_dict()) + "\n"
        self.out_stream.write(line.encode('utf-8'))
        self.out_stream.flush()


class JTLSampleWriter(LDJSONSampleWriter):
    def __init__(self, output_file):
        super(JTLSampleWriter, self).__init__(output_file)

    def __enter__(self):
        obj = super(JTLSampleWriter, self).__enter__()

        fieldnames = ["timeStamp", "elapsed", "Latency", "label", "responseCode", "responseMessage", "success",
                      "allThreads", "bytes"]
        endline = '\n'  # \r will be preprended automatically because out_stream is opened in text mode
        self.writer = csv.DictWriter(self.out_stream, fieldnames=fieldnames, dialect=csv.excel, lineterminator=endline,
                                     encoding='utf-8')
        self.writer.writeheader()
        self.out_stream.flush()

        return obj

    def _write_sample(self, sample, test_count, success_count):
        """
        :type sample: Sample
        :type test_count: int
        :type success_count: int
        """
        self._write_request_subsamples(sample)

    def _get_sample_type(self, sample):
        if sample.path:
            last = sample.path[-1]
            return last.type
        else:
            return None

    def _write_request_subsamples(self, sample):
        if self._get_sample_type(sample) == "request":
            self._write_single_sample(sample)
        elif sample.subsamples:
            for sub in sample.subsamples:
                self._write_request_subsamples(sub)
        else:
            self._write_single_sample(sample)

    def _write_single_sample(self, sample):
        """
        :type sample: Sample
        """
        bytes = sample.extras.get("responseHeadersSize", 0) + 2 + sample.extras.get("responseBodySize", 0)

        message = sample.error_msg
        if not message:
            message = sample.extras.get("responseMessage")
        if not message:
            for sample in sample.subsamples:
                if sample.error_msg:
                    message = sample.error_msg
                    break
                elif sample.extras.get("responseMessage"):
                    message = sample.extras.get("responseMessage")
                    break
        self.writer.writerow({
            "timeStamp": int(1000 * sample.start_time),
            "elapsed": int(1000 * sample.duration),
            "Latency": 0,  # TODO
            "label": sample.test_case,

            "bytes": bytes,

            "responseCode": sample.extras.get("responseCode"),
            "responseMessage": message,
            "allThreads": self.concurrency,  # TODO: there will be a problem aggregating concurrency for rare samples
            "success": "true" if sample.status == "PASSED" else "false",
        })
        self.out_stream.flush()


# noinspection PyPep8Naming
class ApiritifPlugin(Plugin):
    """
    Saves test results in a format suitable for Taurus.
    :type sample_writer: LDJSONSampleWriter
    """

    configSection = 'apiritif-plugin'
    alwaysOn = True

    def __init__(self):
        self.controller = store.SampleController(log=log, session=self.session)
        apiritif.put_into_thread_store(controller=self.controller)

    def startTest(self, event):
        """
        before test run
        """
        test = event.test
        thread.clean_transaction_handlers()
        test_fqn = test.id()  # [package].module.class.method
        suite_name, case_name = test_fqn.split('.')[-2:]
        log.debug("id: %r", test_fqn)
        class_method = case_name

        description = test.shortDescription()
        self.controller.test_info = {
            "test_case": case_name,
            "suite_name": suite_name,
            "test_fqn": test_fqn,
            "description": description,
            "class_method": class_method}
        self.controller.startTest()

    def stopTest(self, event):
        #if not 'NormalShutdown' in self.session.stop_reason
        self.controller.stopTest()

    def reportError(self, event):
        """
        when a test raises an uncaught exception
        :param test:
        :param error:
        :return:
        """
        error = event.testEvent.exc_info

        # test_dict will be None if startTest wasn't called (i.e. exception in setUp/setUpClass)
        # status=BROKEN
        assertion_name = error[0].__name__
        error_msg = str(error[1]).split('\n')[0]
        error_trace = get_trace(error)
        if isinstance(error[1], NormalShutdown):
            self.session.set_stop_reason(f"{error[1].__class__.__name__} for vu #{thread.get_index()}: {error_msg}")
            self.controller.current_sample = None   # partial data mustn't be written
        else:
            if self.controller.current_sample is not None:
                self.controller.addError(assertion_name, error_msg, error_trace)
            else:  # error in test infrastructure (e.g. module setup())
                log.error("\n".join((assertion_name, error_msg, error_trace)))

    def reportFailure(self, event):
        """
        when a test fails
        :param test:
        :param error:

        :return:
        """
        # status=FAILED
        self.controller.addFailure(event.testEvent.exc_info)

    def reportSuccess(self, event):
        """
        when a test passes
        :param test:
        :return:
        """
        self.controller.addSuccess()

    def afterTestRun(self, event):
        """
        After all tests
        """
        if not self.controller.test_count:
            self.session.set_stop_reason("Nothing to test.")


def cmdline_to_params():
    parser = OptionParser()
    parser.add_option('', '--concurrency', action='store', type="int", default=1)
    parser.add_option('', '--iterations', action='store', type="int", default=sys.maxsize)
    parser.add_option('', '--ramp-up', action='store', type="float", default=0)
    parser.add_option('', '--steps', action='store', type="int", default=sys.maxsize)
    parser.add_option('', '--hold-for', action='store', type="float", default=0)
    parser.add_option('', '--result-file-template', action='store', type="str", default="result-%s.csv")
    parser.add_option('', '--verbose', action='store_true', default=False)
    parser.add_option('', "--version", action='store_true', default=False)
    opts, args = parser.parse_args()
    log.debug("%s %s", opts, args)

    if opts.version:
        print(VERSION)
        sys.exit(0)

    params = Params()
    params.concurrency = opts.concurrency
    params.ramp_up = opts.ramp_up
    params.steps = opts.steps
    params.iterations = opts.iterations
    params.hold_for = opts.hold_for

    params.report = opts.result_file_template
    params.tests = args
    params.worker_count = 1  # min(params.concurrency, multiprocessing.cpu_count())
    params.verbose = opts.verbose

    return params


def setup_logging(params):
    logformat = "%(asctime)s:%(levelname)s:%(process)s:%(thread)s:%(name)s:%(message)s"
    apiritif.http.log.setLevel(logging.WARNING)
    if params.verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format=logformat)
    else:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=logformat)
    log.setLevel(logging.INFO)  # TODO: do we need to include apiritif debug logs in verbose mode?


def main():
    cmd_params = cmdline_to_params()
    setup_logging(cmd_params)
    supervisor = Supervisor(cmd_params)
    supervisor.start()
    supervisor.join()


if __name__ == '__main__':
    main()
