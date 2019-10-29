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
import logging
import multiprocessing
import os
import sys
import time
from multiprocessing.pool import ThreadPool
from optparse import OptionParser
from threading import Thread

from nose.config import Config, all_config_files
from nose.core import TestProgram
from nose.loader import defaultTestLoader
from nose.plugins.manager import DefaultPluginManager

import apiritif
import apiritif.store as store
from apiritif.samples import JTLSampleWriter, LDJSONSampleWriter
from apiritif.utils import log


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

        store.set_total(self.params.concurrency)
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
            store.writer = LDJSONSampleWriter(self.params.report)
        else:
            store.writer = JTLSampleWriter(self.params.report)

    def start(self):
        params = list(self._get_thread_params())
        with store.writer:
            self.map(self.run_nose, params)
            log.info("Workers finished, awaiting result writer")
            while not store.writer.is_queue_empty() and store.writer.is_alive():
                time.sleep(0.1)
            log.info("Results written, shutting down")
            self.close()

    def run_nose(self, params):
        """
        :type params: Params
        """
        store.set_index(params.thread_index)
        log.debug("[%s] Starting nose iterations: %s", params.worker_index, params)
        assert isinstance(params.tests, list)
        # argv.extend(['--with-apiritif', '--nocapture', '--exe', '--nologcapture'])

        end_time = self.params.ramp_up + self.params.hold_for
        end_time += time.time() if end_time else 0
        time.sleep(params.delay)

        plugin = ApiritifPlugin()
        store.writer.concurrency += 1

        config = Config(env=os.environ, files=all_config_files(), plugins=DefaultPluginManager())
        config.plugins.addPlugins(extraplugins=[plugin])
        config.testNames = params.tests
        config.verbosity = 3 if params.verbose else 0
        if params.verbose:
            config.stream = open(os.devnull, "w")  # FIXME: use "with", allow writing to file/log

        iteration = 0
        try:
            while True:
                log.debug("Starting iteration:: index=%d,start_time=%.3f", iteration, time.time())
                store.set_iteration(iteration)
                ApiritifTestProgram(config=config)
                log.debug("Finishing iteration:: index=%d,end_time=%.3f", iteration, time.time())

                iteration += 1

                # reasons to stop
                if plugin.stop_reason:
                    log.debug("[%s] finished prematurely: %s", params.worker_index, plugin.stop_reason)
                elif iteration >= params.iterations:
                    log.debug("[%s] iteration limit reached: %s", params.worker_index, params.iterations)
                elif 0 < end_time <= time.time():
                    log.debug("[%s] duration limit reached: %s", params.worker_index, params.hold_for)
                else:
                    continue  # continue if no one is faced

                break
        finally:
            store.writer.concurrency -= 1

            if params.verbose:
                config.stream.close()

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


class ApiritifTestProgram(TestProgram):
    def __init__(self, *args, **kwargs):
        super(ApiritifTestProgram, self).__init__(*args, **kwargs)
        self.testNames = None

    def parseArgs(self, argv):
        self.exit = False
        self.testNames = self.config.testNames
        self.testLoader = defaultTestLoader(config=self.config)
        self.createTests()


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
