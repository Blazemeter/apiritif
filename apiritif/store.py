# temporary exchanger for ApiritifPlugin stuff
import time
import traceback

import apiritif
from apiritif.samples import ApiritifSampleExtractor, Sample, PathComponent
from apiritif.utils import get_trace

writer = None


class SampleController(object):
    def __init__(self, log):
        self.current_sample = None  # todo: recreate it from plugin's template every transaction
        self.success_count = None
        self.log = log
        self.test_count = 0
        self.success_count = 0
        self.apiritif_extractor = ApiritifSampleExtractor()
        self.tran_mode = False  # it's regular test (without smart transaction) by default
        self.start_time = None
        self.end_time = None
        self.test_info = {}

    def beforeTest(self):
        self.current_sample = Sample(
            test_case=self.test_info["test_case"],
            test_suite=self.test_info["suite_name"],
            start_time=time.time(),
            status="SKIPPED")
        self.current_sample.extras.update({
            "file": self.test_info["test_file"],
            "full_name": self.test_info["test_fqn"],
            "description": self.test_info["description"]
        })
        module_fqn_parts = self.test_info["module_fqn"].split('.')
        for item in module_fqn_parts[:-1]:
            self.current_sample.path.append(PathComponent("package", item))
        self.current_sample.path.append(PathComponent("module", module_fqn_parts[-1]))

        if "." in self.test_info["class_method"]:  # TestClass.test_method
            class_name, method_name = self.test_info["class_method"].split('.')[:2]
            self.current_sample.path.extend([
                PathComponent("class", class_name),
                PathComponent("method", method_name)])
        else:  # test_func
            self.current_sample.path.append(PathComponent("func", self.test_info["class_method"]))

        self.log.debug("Test method path: %r", self.current_sample.path)

        self.test_count += 1

    def startTest(self):
        self.start_time = time.time()

    def stopTest(self, is_transaction=False):
        if self.tran_mode == is_transaction:
            self.end_time = time.time()

    def addError(self, assertion_name, error_msg, error_trace, is_transaction=False):
        if self.tran_mode == is_transaction:
            self.current_sample.add_assertion(assertion_name, {"args": [], "kwargs": {}})
            self.current_sample.set_assertion_failed(assertion_name, error_msg, error_trace)

    def addFailure(self, error, is_transaction=False):
        if self.tran_mode == is_transaction:
            assertion_name = error[0].__name__
            error_msg = str(error[1]).split('\n')[0]
            error_trace = get_trace(error)
            self.current_sample.add_assertion(assertion_name, {"args": [], "kwargs": {}})
            self.current_sample.set_assertion_failed(assertion_name, error_msg, error_trace)

    def addSuccess(self, is_transaction=False):
        if self.tran_mode == is_transaction:
            self.current_sample.status = "PASSED"
            self.success_count += 1

    def afterTest(self, is_transaction=False):
        if self.tran_mode == is_transaction:
            if self.end_time is None:
                self.end_time = time.time()
            self.current_sample.duration = self.end_time - self.current_sample.start_time

            samples_processed = self._process_apiritif_samples(self.current_sample)
            if not samples_processed:
                self._process_sample(self.current_sample)

            self.current_sample = None

    def _process_apiritif_samples(self, sample):
        samples = []

        # get list of events
        recording = apiritif.recorder.pop_events(from_ts=self.start_time, to_ts=self.end_time)

        try:
            if recording:
                # convert requests (events) to samples
                samples = self.apiritif_extractor.parse_recording(recording, sample)
        except BaseException as exc:
            self.log.debug("Couldn't parse recording: %s", traceback.format_exc())
            self.log.warning("Couldn't parse recording: %s", exc)

        for sample in samples:
            self._process_sample(sample)  # just write to disk

        return len(samples)

    def _process_sample(self, sample):
        writer.add(sample, self.test_count, self.success_count)
