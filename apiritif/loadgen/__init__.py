"""
destination file format - how to work in functional (LDJSON) vs performance mode (CSV? JTL?)
logging approach - is STDOUT/STDERR enough? how to minimize files written?
how to implement hits/s control/shape?

nosetests plugin (might be part of worker)
"""

import logging
import multiprocessing
import sys
from optparse import OptionParser

log = logging.getLogger("loadgen")


def supervisor():
    """
    apiritif-loadgen CLI utility
        spawns workers, spreads them over time
        if concurrency < CPU_count: workers=concurrency else workers=CPU_count
        distribute load among them equally +-1
        smart delay of subprocess startup to spread ramp-up gracefully (might be responsibility of worker
        overwatch workers, kill them when terminated
        probably reports through stdout log the names of report files
    """

    args, opts = parse_options()
    log.debug("%s %s", opts, args)

    worker_count = min(opts.concurrency, multiprocessing.cpu_count())
    log.info("Total workers: %s", worker_count)

    def worker(args):
        idx, conc = args
        results = opts.result_file_template % idx
        log.info("Adding worker: idx=%s\tconcurrency=%s\tresults=%s", idx, conc, results)
        cmd = [
            '--concurrency', conc,
            '--iterations', opts.iterations,
            '--ramp-up', opts.ramp_up,
            '--steps', opts.steps,
            '--hold-for', opts.hold_for,
            '--result-file', results,
            '--worker-index', idx,
            '--workers-total', worker_count,
        ]

    workers = multiprocessing.Pool(processes=worker_count)
    workers.map(worker, concurrency_slicer(worker_count, opts.concurrency))

    """
    for idx, conc in concurrency_slicer(worker_count, opts.concurrency):
        workers.append(cmd)
    """


def concurrency_slicer(worker_count, concurrency):
    total_concurrency = 0.0
    inc = concurrency / float(worker_count)
    assert inc >= 1
    for idx in range(0, worker_count):
        progress = (idx + 1) * inc
        conc = round(progress - total_concurrency)
        total_concurrency += conc
        assert conc > 0
        assert total_concurrency >= 0
        log.debug("Idx: %s, concurrency: %s", idx, conc)
        yield idx, conc

    assert total_concurrency == concurrency
    # sys.executable, args


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
    supervisor()
