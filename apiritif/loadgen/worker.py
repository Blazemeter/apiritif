
import logging
import sys
from optparse import OptionParser


def worker():
    """
    apiritif-loadgen-worker CLI utility
        creates concurrent threads running nosetests (is nose able to run multithreaded at all?)
        performs ramp-up of threads (with steps if needed)
        accepts params:
            concurrency - default 1
            iterations - by default infinite (or 1?)
            ramp-up and steps
            hold-for time
            destination file - (not pattern!)
            sequential ID and total process count - for scripts to know, can be env var
    """
    parser = OptionParser()
    parser.add_option('', '--concurrency', action='store', default=1)
    parser.add_option('', '--iterations', action='store', default=sys.maxsize)
    parser.add_option('', '--ramp-up', action='store', default=0)
    parser.add_option('', '--steps', action='store', default=sys.maxsize)
    parser.add_option('', '--hold-for', action='store', default=0)
    parser.add_option('', '--result-file', action='store', default="result0.csv")  # TODO?
    parser.add_option('', '--worker-index', action='store', default=0)
    parser.add_option('', '--workers-total', action='store', default=1)
    opts, args = parser.parse_args()


if __name__ == '__main__':
    # do the subprocess starter utility
    logging.basicConfig(level=logging.DEBUG)
    worker()
