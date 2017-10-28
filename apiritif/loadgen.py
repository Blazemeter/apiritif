"""
destination file format - how to work in functional (LDJSON) vs performance mode (CSV? JTL?)
logging approach - is STDOUT/STDERR enough? how to minimize files written?
how to implement hits/s control/shape?

nosetests plugin (might be part of worker)
"""

import copy
import csv
import json
import logging
import multiprocessing
import sys
import time
import traceback
from multiprocessing.pool import ThreadPool
from optparse import OptionParser
from threading import Thread

import nose
from nose.plugins import Plugin

import apiritif

log = logging.getLogger("loadgen")


def spawn_worker(params):
    """
    This method has to be module level function

    :type params: Params
    """
    log.info("Adding worker: idx=%s\tconcurrency=%s\tresults=%s", params.index, params.concurrency, params.results_file)

    worker = Worker(params)
    worker.start()
    worker.join()


class Params(object):
    def __init__(self):
        super(Params, self).__init__()
        self.index = None
        self.worker_count = None
        self.results_file = None

        self.concurrency = 1
        self.iterations = 1
        self.ramp_up = 0
        self.steps = 0
        self.hold_for = 0

        self.tests = None


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
        self.steps = options.steps
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

            params = Params()
            params.index = idx
            params.concurrency = conc
            params.results_file = self.result_file_template % idx
            params.worker_count = worker_count
            params.tests = self.tests
            params.iterations = self.iterations
            params.ramp_up = self.ramp_up
            params.steps = self.steps

            yield params

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
    def __init__(self, params):
        """
        :type params: Params
        """
        super(Worker, self).__init__(params.concurrency)
        self.params = params

    def start(self):
        self.map(self.run_nose, self._get_thread_params())
        self.close()

    def run_nose(self, params):
        logging.debug("Starting nose iterations: %s", params)
        report_file, files, iteration_limit, delay = params
        assert isinstance(files, list)
        argv = [__file__, '-v']
        argv.extend(files)
        argv.extend(['--with-apiritif', '--nocapture', '--exe', '--nologcapture'])

        time.sleep(delay)

        if report_file.lower().endswith(".ldjson"):
            writer = LDJSONSampleWriter(report_file)
        else:
            writer = JTLSampleWriter(report_file)

        with writer:
            iteration = 0
            plugin = ApiritifPlugin(writer)
            while True:
                nose.run(addplugins=[plugin], argv=argv)
                iteration += 1
                if iteration >= iteration_limit:
                    break
        log.debug("Done nose iterations")

    def __reduce__(self):
        raise NotImplementedError()

    def _get_thread_params(self):
        for thr_idx in range(self._processes):
            delay = thr_idx * float(self.params.ramp_up) / self.params.concurrency
            yield self.params.results_file, self.params.tests, self.params.iterations, delay


class LDJSONSampleWriter(object):
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

        fieldnames = ["timeStamp", "elapsed", "label", "responseCode", "responseMessage", "success", "allThreads"]
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
        self.writer.writerow({
            "timeStamp": int(1000 * sample.start_time),
            "elapsed": int(1000 * sample.duration),
            "label": sample.test_case,

            "responseCode": None,  # TODO
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


class Sample(object):
    def __init__(self, test_suite=None, test_case=None, status=None, start_time=None, duration=None,
                 error_msg=None, error_trace=None):
        self.test_suite = test_suite  # test label (test method name)
        self.test_case = test_case  # test suite name (class name)
        self.status = status  # test status (PASSED/FAILED/BROKEN/SKIPPED)
        self.start_time = start_time  # test start time
        self.duration = duration  # test duration
        self.error_msg = error_msg  # short error message
        self.error_trace = error_trace  # traceback of a failure
        self.extras = {}  # extra info: ('file' - location, 'full_name' - full qualified name, 'decsription' - docstr)
        self.subsamples = []  # subsamples list

    def add_subsample(self, sample):
        self.subsamples.append(sample)

    def to_dict(self):
        # type: () -> dict
        return {
            "test_suite": self.test_suite,
            "test_case": self.test_case,
            "status": self.status,
            "start_time": self.start_time,
            "duration": self.duration,
            "error_msg": self.error_msg,
            "error_trace": self.error_trace,
            "extras": self.extras,
            "subsamples": [sample.to_dict() for sample in self.subsamples],
        }

    def __repr__(self):
        return "Sample(%r)" % self.to_dict()


class ApiritifSampleExtractor(object):
    def parse_recording(self, recording, test_case_sample):
        """

        :type recording: list[apiritif.Event]
        :type test_case_sample: Sample
        :rtype: list[Sample]
        """
        test_case_name = test_case_sample.test_case
        active_transactions = [test_case_sample]
        response_map = {}  # response -> sample
        transactions_present = False
        for item in recording:
            if isinstance(item, apiritif.Request):
                sample = Sample(
                    test_suite=test_case_name,
                    test_case=item.address,
                    status="PASSED",
                    start_time=item.timestamp,
                    duration=item.response.elapsed.total_seconds(),
                )
                extras = self._extract_extras(item)
                if extras:
                    sample.extras.update(extras)
                response_map[item.response] = sample
                active_transactions[-1].add_subsample(sample)
            elif isinstance(item, apiritif.TransactionStarted):
                transactions_present = True
                tran_sample = Sample(test_case=item.transaction_name, test_suite=test_case_name)
                active_transactions.append(tran_sample)
            elif isinstance(item, apiritif.TransactionEnded):
                tran = item.transaction
                tran_sample = active_transactions.pop()
                assert tran_sample.test_case == item.transaction_name
                tran_sample.start_time = tran.start_time()
                tran_sample.duration = tran.duration()
                if tran.success is None:
                    tran_sample.status = "PASSED"
                    for sample in tran_sample.subsamples:
                        if sample.status in ("FAILED", "BROKEN"):
                            tran_sample.status = sample.status
                            tran_sample.error_msg = sample.error_msg
                            tran_sample.error_trace = sample.error_trace
                elif tran.success:
                    tran_sample.status = "PASSED"
                else:
                    tran_sample.status = "FAILED"
                    tran_sample.error_msg = tran.error_message

                extras = copy.deepcopy(tran.extras())
                extras.update(self._extras_dict(tran.name, "", tran.response_code(), "", {},
                                                tran.response() or "", len(tran.response() or ""),
                                                tran.duration(), tran.request() or "", {}, {}))
                tran_sample.extras = extras

                active_transactions[-1].add_subsample(tran_sample)
            elif isinstance(item, apiritif.Assertion):
                sample = response_map.get(item.response, None)
                if sample is None:
                    raise ValueError("Found assertion for unknown response")
                if "assertions" not in sample.extras:
                    sample.extras["assertions"] = []
                sample.extras["assertions"].append({
                    "name": item.name,
                    "isFailed": False,
                    "failureMessage": "",
                })
            elif isinstance(item, apiritif.AssertionFailure):
                sample = response_map.get(item.response, None)
                if sample is None:
                    raise ValueError("Found assertion failure for unknown response")
                for ass in sample.extras.get("assertions", []):
                    if ass["name"] == item.name:
                        ass["isFailed"] = True
                        ass["failureMessage"] = item.failure_message
                        sample.status = "FAILED"
                        sample.error_msg = item.failure_message
            else:
                raise ValueError("Unknown kind of event in apiritif recording: %s" % item)

        if len(active_transactions) != 1:
            # TODO: shouldn't we auto-balance them?
            raise ValueError("Can't parse apiritif recordings: unbalanced transactions")

        toplevel_sample = active_transactions.pop()

        # do not capture toplevel sample if transactions were used
        if transactions_present:
            return toplevel_sample.subsamples
        else:
            return [toplevel_sample]

    @staticmethod
    def _headers_from_dict(headers):
        return "\n".join(key + ": " + value for key, value in headers.items())

    @staticmethod
    def _cookies_from_dict(cookies):
        return "; ".join(key + "=" + value for key, value in cookies.items())

    def _extras_dict(self, url, method, status_code, reason, response_headers, response_body, response_size,
                     response_time, request_body, request_cookies, request_headers):
        record = {
            'responseCode': status_code,
            'responseMessage': reason,
            'responseTime': response_time,
            'connectTime': 0,
            'latency': 0,
            'responseSize': response_size,
            'requestSize': 0,
            'requestMethod': method,
            'requestURI': url,
            'assertions': [],  # will be filled later
            'responseBody': response_body,
            'requestBody': request_body,
            'requestCookies': request_cookies,
            'requestHeaders': request_headers,
            'responseHeaders': response_headers,
        }
        record["requestCookiesRaw"] = self._cookies_from_dict(record["requestCookies"])
        record["responseBodySize"] = len(record["responseBody"])
        record["requestBodySize"] = len(record["requestBody"])
        record["requestCookiesSize"] = len(record["requestCookiesRaw"])
        record["requestHeadersSize"] = len(self._headers_from_dict(record["requestHeaders"]))
        record["responseHeadersSize"] = len(self._headers_from_dict(record["responseHeaders"]))
        return record

    def _extract_extras(self, request_event):
        resp = request_event.response
        req = request_event.request

        return self._extras_dict(
            req.url, req.method, resp.status_code, resp.reason,
            dict(resp.headers), resp.text, len(resp.content), resp.elapsed.total_seconds(),
            req.body or "", dict(request_event.session.cookies), dict(resp._request.headers)
        )


def parse_options():
    parser = OptionParser()
    parser.add_option('', '--concurrency', action='store', type="int", default=1)
    parser.add_option('', '--iterations', action='store', type="int", default=sys.maxsize)
    parser.add_option('', '--ramp-up', action='store', type="float", default=0)
    parser.add_option('', '--steps', action='store', type="int", default=sys.maxsize)
    parser.add_option('', '--hold-for', action='store', type="float", default=0)
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
