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

import time
import traceback

from nose.plugins import Plugin

import apiritif
import apiritif.store as store
from apiritif.samples import ApiritifSampleExtractor, Sample, PathComponent
from apiritif.samples import LDJSONSampleWriter
from apiritif.utils import NormalShutdown, log
from apiritif.utils import get_trace


# noinspection PyPep8Naming
class ApiritifPlugin(Plugin):
    """
    Saves test results in a format suitable for Taurus.
    :type sample_writer: LDJSONSampleWriter
    """

    name = 'apiritif'
    enabled = False

    def __init__(self):
        super(ApiritifPlugin, self).__init__()
        self.controller = TransactionController(log)
        apiritif.put_into_thread_store(controller=self.controller)  # parcel for smart_transactions
        self.stop_reason = ""

    def finalize(self, result):
        """
        After all tests
        """
        if not self.controller.test_count:
            raise RuntimeError("Nothing to test.")

    def beforeTest(self, test):
        """
        before test run
        """
        store.clean_transaction_handlers()
        addr = test.address()  # file path, package.subpackage.module, class.method
        test_file, module_fqn, class_method = addr
        test_fqn = test.id()  # [package].module.class.method
        suite_name, case_name = test_fqn.split('.')[-2:]
        log.debug("Addr: %r", addr)
        log.debug("id: %r", test_fqn)

        if class_method is None:
            class_method = case_name

        description = test.shortDescription()
        self.controller.test_info = {
            "test_case": case_name,
            "suite_name": suite_name,
            "test_file": test_file,
            "test_fqn": test_fqn,
            "description": description,
            "module_fqn": module_fqn,
            "class_method": class_method}
        self.controller.beforeTest()  # create template of current_sample

    def startTest(self, test):
        self.controller.startTest()

    def stopTest(self, test):
        self.controller.stopTest()

    def afterTest(self, test):
        self.controller.afterTest()

    def addError(self, test, error):
        """
        when a test raises an uncaught exception
        :param test:
        :param error:
        :return:
        """
        # test_dict will be None if startTest wasn't called (i.e. exception in setUp/setUpClass)
        # status=BROKEN
        assertion_name = error[0].__name__
        error_msg = str(error[1]).split('\n')[0]
        error_trace = get_trace(error)
        if self.controller.current_sample is not None:
            self.controller.addError(assertion_name, error_msg, error_trace)
        else:  # error in test infrastructure (e.g. module setup())
            log.error("\n".join((assertion_name, error_msg, error_trace)))

    @staticmethod
    def isNormalShutdown(cls):
        cls_full_name = ".".join((cls.__module__, cls.__name__))
        ns_full_name = ".".join((NormalShutdown.__module__, NormalShutdown.__name__))
        return cls_full_name == ns_full_name

    def handleError(self, test, error):
        if self.isNormalShutdown(error[0]):
            self.add_stop_reason(error[1].args[0])  # remember it for run_nose() cycle
            return True
        else:
            return False

    def add_stop_reason(self, msg):
        if self.stop_reason:
            self.stop_reason += "\n"

        self.stop_reason += msg

    def addFailure(self, test, error):
        """
        when a test fails
        :param test:
        :param error:

        :return:
        """
        # status=FAILED
        self.controller.addFailure(error)

    def addSuccess(self, test):
        """
        when a test passes
        :param test:
        :return:
        """
        self.controller.addSuccess()


class TransactionController(object):
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
            self.current_sample.add_assertion(assertion_name)
            self.current_sample.set_assertion_failed(assertion_name, error_msg, error_trace)

    def addFailure(self, error, is_transaction=False):
        if self.tran_mode == is_transaction:
            assertion_name = error[0].__name__
            error_msg = str(error[1]).split('\n')[0]
            error_trace = get_trace(error)
            self.current_sample.add_assertion(assertion_name)
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
        store.writer.add(sample, self.test_count, self.success_count)
