# temporary exchanger for ApiritifPlugin data
import time
import apiritif
import traceback

from apiritif.utils import get_trace
from apiritif.samples import ApiritifSampleExtractor, Sample, PathComponent

writer = None


class SampleController(object):
    def __init__(self, log):
        self.current_sample = None  # todo: recreate it from plugin's template every transaction
        self.success_count = None
        self.log = log
        self.test_count = 0
        self.success_count = 0
        self.apiritif_extractor = ApiritifSampleExtractor()
        self.test_mode = None
        self.start_time = None
        self.end_time = None

    def beforeTest(self, case_name, suite_name, test_file, test_fqn, description, module_fqn, class_method):
        self.test_mode = True   # isn't under smart_transaction control by default
        # todo: save fields for recreation purpose (in transaction)
        self.current_sample = Sample(
            test_case=case_name,
            test_suite=suite_name,
            start_time=time.time(),
            status="SKIPPED")
        self.current_sample.extras.update({
            "file": test_file,
            "full_name": test_fqn,
            "description": description
        })
        module_fqn_parts = module_fqn.split('.')
        for item in module_fqn_parts[:-1]:
            self.current_sample.path.append(PathComponent("package", item))
        self.current_sample.path.append(PathComponent("module", module_fqn_parts[-1]))

        if "." in class_method:  # TestClass.test_method
            class_name, method_name = class_method.split('.')[:2]
            self.current_sample.path.extend([
                PathComponent("class", class_name),
                PathComponent("method", method_name)])
        else:  # test_func
            self.current_sample.path.append(PathComponent("func", class_method))

        self.log.debug("Test method path: %r", self.current_sample.path)

        self.test_count += 1

    def startTest(self):
        self.start_time = time.time()

    def stopTest(self):
        if not self.test_mode:
            return

        self.end_time = time.time()

    def addError(self, assertion_name, error_msg, error_trace):
        if not self.test_mode:
            return

        self.current_sample.add_assertion(assertion_name)
        self.current_sample.set_assertion_failed(assertion_name, error_msg, error_trace)

    def addFailure(self, error):
        if not self.test_mode:
            return

        assertion_name = error[0].__name__
        error_msg = str(error[1]).split('\n')[0]
        error_trace = get_trace(error)
        self.current_sample.add_assertion(assertion_name)
        self.current_sample.set_assertion_failed(assertion_name, error_msg, error_trace)

    def addSuccess(self):
        if not self.test_mode:
            return

        self.current_sample.status = "PASSED"
        self.success_count += 1

    def afterTest(self):
        if not self.test_mode:
            return

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
        with open('/tmp/o.txt', 'a') as f:
            f.write("plugin: %s, extractor: %s, recorder: %s [%s]\n" %
                    (id(self), id(self.apiritif_extractor), id(apiritif.recorder), len(recording)))

        try:
            if recording:
                # convert requests (events) to samples
                samples = self.apiritif_extractor.parse_recording(recording, sample)
        except BaseException as exc:
            self.log.debug("Couldn't parse recording: %s", traceback.format_exc())
            self.log.warning("Couldn't parse recording: %s", exc)

        for sample in samples:
            self._process_sample(sample)    # just write to disk

        return len(samples)

    def _process_sample(self, sample):
        writer.add(sample, self.test_count, self.success_count)
