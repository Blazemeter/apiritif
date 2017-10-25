"""
destination file format - how to work in functional (LDJSON) vs performance mode (CSV? JTL?)
logging approach - is STDOUT/STDERR enough? how to minimize files written?
how to implement hits/s control/shape?

nosetests plugin (might be part of worker)
"""

import logging
import multiprocessing
import sys
import time
from multiprocessing.pool import ThreadPool
from optparse import OptionParser
from threading import Thread

import nose

log = logging.getLogger("loadgen")


def spawn_worker(params):
    """
    This method has to be module level function

    :return:
    """
    idx, conc, res_file, tests, iterations = params
    log.info("Adding worker: idx=%s\tconcurrency=%s\tresults=%s", idx, conc, res_file)

    worker = Worker(conc, res_file, tests, iterations)
    worker.start()
    worker.join()


class Supervisor(Thread):
    """
    apiritif-loadgen CLI utility
        overwatch workers, kill them when terminated
        probably reports through stdout log the names of report files
    """

    def __init__(self, options, args):
        super(Supervisor, self).__init__(target=self._start_workers)
        self.setDaemon(True)
        self.setName(self.__class__.__name__)

        self.concurrency = options.concurrency
        self.ramp_up = options.ramp_up
        self.iterations = options.iterations
        self.hold_for = options.hold_for

        self.result_file_template = options.result_file_template
        self.tests = args

    def _concurrency_slicer(self, worker_count, concurrency):
        total_concurrency = 0
        inc = concurrency / float(worker_count)
        assert inc >= 1
        for idx in range(0, worker_count):
            progress = (idx + 1) * inc
            conc = int(round(progress - total_concurrency))
            total_concurrency += conc
            assert conc > 0
            assert total_concurrency >= 0
            log.debug("Idx: %s, concurrency: %s", idx, conc)
            yield idx, conc, self.result_file_template % idx, self.tests, self.iterations

        assert total_concurrency == concurrency

    def _start_workers(self):
        worker_count = min(self.concurrency, multiprocessing.cpu_count())
        log.info("Total workers: %s", worker_count)

        workers = multiprocessing.Pool(processes=worker_count)
        workers.map(spawn_worker, self._concurrency_slicer(worker_count, self.concurrency))
        workers.close()
        workers.join()
        # TODO: watch the total test duration, if set


class Worker(ThreadPool):
    def __init__(self, concurrency, results_file, tests, iterations):
        super(Worker, self).__init__(concurrency)
        self.iterations = iterations
        self.results_file = results_file
        self.tests = tests

    def start(self):
        params = ((self.results_file, self.tests, self.iterations),) * self._processes
        self.map(self.run_nose, params)
        self.close()

    def run_nose(self, params):
        logging.debug("Starting nose iterations: %s", params)
        report_file, files, iteration_limit = params
        assert isinstance(files, list)
        argv = [__file__, '-v']
        argv.extend(files)
        argv.extend(['--nocapture', '--exe', '--nologcapture'])

        iteration = 0
        while True:
            nose.run(addplugins=[], argv=argv)
            iteration += 1
            if iteration >= iteration_limit:
                break
        log.debug("Done nose iterations")

    def __reduce__(self):
        raise NotImplementedError()


def parse_options():
    parser = OptionParser()
    parser.add_option('', '--concurrency', action='store', type="int", default=1)
    parser.add_option('', '--iterations', action='store', type="int", default=sys.maxsize)
    parser.add_option('', '--ramp-up', action='store', type="int", default=0)
    parser.add_option('', '--steps', action='store', type="int", default=sys.maxsize)
    parser.add_option('', '--hold-for', action='store', type="int", default=0)
    parser.add_option('', '--result-file-template', action='store', type="str", default="result-%s.csv")  # TODO?
    parser.add_option('', '--verbose', action='store_true', default=False)
    opts, args = parser.parse_args()
    return args, opts


if __name__ == '__main__':
    # do the subprocess starter utility
    logging.basicConfig(level=logging.DEBUG)
    args1, opts1 = parse_options()
    log.debug("%s %s", opts1, args1)
    supervisor = Supervisor(opts1, args1)
    supervisor.start()
    while supervisor.isAlive():
        time.sleep(1)
