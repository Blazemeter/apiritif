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
import csv
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

from nose.config import Config, all_config_files
from nose.core import TestProgram
from nose.plugins import Plugin
from nose.plugins.manager import DefaultPluginManager

import apiritif
from apiritif.samples import ApiritifSampleExtractor, Sample

log = logging.getLogger("loadgen")


# TODO how to implement hits/s control/shape?

def spawn_worker(params):
    """
    This method has to be module level function

    :type params: Params
    """
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
        self.report = None

        self.delay = 0

        self.concurrency = 1
        self.iterations = 1
        self.ramp_up = 0
        self.steps = 0
        self.hold_for = 0

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
        self.setDaemon(True)
        self.setName(self.__class__.__name__)

        self.params = params

    def _concurrency_slicer(self, ):
        total_concurrency = 0
        inc = self.params.concurrency / float(self.params.worker_count)
        assert inc >= 1
        for idx in range(0, self.params.worker_count):
            progress = (idx + 1) * inc
            conc = int(round(progress - total_concurrency))
            total_concurrency += conc
            assert conc > 0
            assert total_concurrency >= 0
            log.debug("Idx: %s, concurrency: %s", idx, conc)

            params = copy.deepcopy(self.params)
            params.worker_index = idx
            params.concurrency = conc
            params.report = self.params.report % idx
            params.worker_count = self.params.worker_count

            yield params

        assert total_concurrency == self.params.concurrency

    def _start_workers(self):
        log.info("Total workers: %s", self.params.worker_count)

        workers = multiprocessing.Pool(processes=self.params.worker_count)
        args = list(self._concurrency_slicer())
        workers.map(spawn_worker, args)
        workers.close()
        workers.join()
        # TODO: watch the total test duration, if set, 'cause iteration might last very long


class Worker(ThreadPool):
    def __init__(self, params):
        """
        :type params: Params
        """
        super(Worker, self).__init__(params.concurrency)
        self.params = params
        if self.params.report.lower().endswith(".ldjson"):
            self._writer = LDJSONSampleWriter(self.params.report)
        else:
            self._writer = JTLSampleWriter(self.params.report)

    def start(self):
        params = list(self._get_thread_params())
        with self._writer:
            self.map(self.run_nose, params)
            self.close()

    def run_nose(self, params):
        """
        :type params: Params
        """
        log.debug("[%s] Starting nose iterations: %s", params.worker_index, params)
        assert isinstance(params.tests, list)
        argv = [__file__, '-v']
        argv.extend(['--with-apiritif', '--nocapture', '--exe', '--nologcapture', '--verbosity', '0'])
        argv.extend(params.tests)

        start_time = time.time()
        time.sleep(params.delay)

        iteration = 0
        plugin = ApiritifPlugin(self._writer)

        config = Config(env=os.environ, files=all_config_files(), plugins=DefaultPluginManager())
        config.stream = open(os.devnull, "w")  # FIXME: use "with", allow writing to file/log

        while True:
            test_program = TestProgram(exit=False, argv=argv, config=config, addplugins=[plugin])

            iteration += 1
            if iteration >= params.iterations:
                log.debug("[%s] iteration limit reached: %s", params.worker_index, params.iterations)
                break

            if 0 < self.params.hold_for < (time.time() - start_time):
                log.debug("[%s] duration limit reached: %s", params.worker_index, params.hold_for)
                break

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
            params.delay = delay
            yield params


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
        self._writer_thread.setDaemon(True)
        self._writer_thread.setName(self.__class__.__name__)

    def __enter__(self):
        self.out_stream = open(self.output_file, "wt")
        self._writing = True
        self._writer_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._writing = False
        self._writer_thread.join()
        self.out_stream.close()

    def add(self, sample, test_count, success_count):
        self._samples_queue.put_nowait((sample, test_count, success_count))

    def _writer(self):
        while self._writing:
            while not self._samples_queue.empty():
                sample, test_count, success_count = self._samples_queue.get(block=True)
                self._write_sample(sample, test_count, success_count)

    def _write_sample(self, sample, test_count, success_count):
        self.out_stream.write("%s\n" % json.dumps(sample.to_dict()))
        self.out_stream.flush()

        report_pattern = "%s,Total:%d Passed:%d Failed:%d\n"
        failed_count = test_count - success_count
        sys.stdout.write(report_pattern % (sample.test_case, test_count, success_count, failed_count))
        sys.stdout.flush()


class JTLSampleWriter(LDJSONSampleWriter):
    def __init__(self, output_file):
        super(JTLSampleWriter, self).__init__(output_file)

    def __enter__(self):
        obj = super(JTLSampleWriter, self).__enter__()

        fieldnames = ["timeStamp", "elapsed", "Latency", "label", "responseCode", "responseMessage", "success",
                      "allThreads"]
        self.writer = csv.DictWriter(self.out_stream, fieldnames=fieldnames, dialect=csv.excel)
        self.writer.writeheader()
        self.out_stream.flush()

        return obj

    def _write_sample(self, sample, test_count, success_count):
        """
        :type sample: Sample
        :type test_count: int
        :type success_count: int
        """
        response_code = sample.extras.get("responseCode")
        # if transaction doesn't have responseCode set - try to grab it from last request
        if response_code is None and sample.subsamples:
            response_code = sample.subsamples[-1].extras.get("responseCode")

        self.writer.writerow({
            "timeStamp": int(1000 * sample.start_time),
            "elapsed": int(1000 * sample.duration),
            "Latency": 0,  # TODO
            "label": sample.test_case,

            "responseCode": response_code,
            "responseMessage": sample.error_msg,
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

    name = 'apiritif'
    enabled = True

    def __init__(self, sample_writer):
        super(ApiritifPlugin, self).__init__()
        self.sample_writer = sample_writer
        self.test_count = 0
        self.success_count = 0
        self.current_sample = None
        self.apiritif_extractor = ApiritifSampleExtractor()

    def begin(self):
        """
        Before any test runs
        open descriptor here
        :return:
        """
        self.sample_writer.concurrency += 1

    def finalize(self, result):
        """
        After all tests
        :param result:
        :return:
        """
        self.sample_writer.concurrency -= 1
        del result
        if not self.test_count:
            raise RuntimeError("Nothing to test.")

    def startTest(self, test):
        """
        before test run
        :param test:
        :return:
        """
        test_file, _, _ = test.address()  # file path, module name, class.method
        test_fqn = test.id()  # [package].module.class.method
        class_name, method_name = test_fqn.split('.')[-2:]

        self.current_sample = Sample(test_case=method_name,
                                     test_suite=class_name,
                                     start_time=time.time(),
                                     status="SKIPPED")
        self.current_sample.extras.update({
            "file": test_file,
            "full_name": test_fqn,
            "description": test.shortDescription()
        })

    def addError(self, test, error):
        """
        when a test raises an uncaught exception
        :param test:
        :param error:
        :return:
        """
        # test_dict will be None if startTest wasn't called (i.e. exception in setUp/setUpClass)
        if self.current_sample is not None:
            self.current_sample.status = "BROKEN"
            self.current_sample.error_msg = str(error[1]).split('\n')[0]
            self.current_sample.error_trace = self._get_trace(error)

    @staticmethod
    def _get_trace(error):
        if sys.version > '3':
            # noinspection PyArgumentList
            lines = traceback.format_exception(*error, chain=not isinstance(error[1], str))
        else:
            lines = traceback.format_exception(*error)
        return ''.join(lines).rstrip()

    def addFailure(self, test, error):
        """
        when a test fails
        :param test:
        :param error:

        :return:
        """
        self.current_sample.status = "FAILED"
        self.current_sample.error_msg = str(error[1]).split('\n')[0]
        self.current_sample.error_trace = self._get_trace(error)

    def addSkip(self, test):
        """
        when a test is skipped
        :param test:
        :return:
        """
        self.current_sample.status = "SKIPPED"

    def addSuccess(self, test):
        """
        when a test passes
        :param test:
        :return:
        """
        self.current_sample.status = "PASSED"
        self.success_count += 1

    def stopTest(self, test):
        """
        after the test has been run
        :param test:
        :return:
        """
        self.current_sample.duration = time.time() - self.current_sample.start_time

        samples_processed = self._process_apiritif_samples(self.current_sample)
        if not samples_processed:
            self._process_sample(self.current_sample)

        self.current_sample = None

    def _process_apiritif_samples(self, sample):
        samples_processed = 0
        test_case = sample.test_case

        recording = apiritif.recorder.get_recording(test_case, clear=True)
        if not recording:
            return samples_processed

        samples = self.apiritif_extractor.parse_recording(recording, sample)
        for sample in samples:
            samples_processed += 1
            self._process_sample(sample)

        return samples_processed

    def _process_sample(self, sample):
        self.test_count += 1
        self.sample_writer.add(sample, self.test_count, self.success_count)


def cmdline_to_params():
    parser = OptionParser()
    parser.add_option('', '--concurrency', action='store', type="int", default=1)
    parser.add_option('', '--iterations', action='store', type="int", default=sys.maxsize)
    parser.add_option('', '--ramp-up', action='store', type="float", default=0)
    parser.add_option('', '--steps', action='store', type="int", default=sys.maxsize)
    parser.add_option('', '--hold-for', action='store', type="float", default=0)
    parser.add_option('', '--result-file-template', action='store', type="str", default="result-%s.csv")
    parser.add_option('', '--verbose', action='store_true', default=False)
    opts, args = parser.parse_args()
    log.debug("%s %s", opts, args)

    params = Params()
    params.concurrency = opts.concurrency
    params.ramp_up = opts.ramp_up
    params.steps = opts.steps
    params.iterations = opts.iterations
    params.hold_for = opts.hold_for

    params.report = opts.result_file_template
    params.tests = args
    params.worker_count = min(params.concurrency, multiprocessing.cpu_count())

    return params


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    apiritif.http.log.setLevel(logging.WARNING)

    supervisor = Supervisor(cmdline_to_params())
    supervisor.start()
    while supervisor.isAlive():
        time.sleep(1)
