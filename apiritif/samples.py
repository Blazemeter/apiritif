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

import apiritif
import copy


class Assertion(object):
    def __init__(self, name, ):
        self.name = name
        self.failed = False
        self.error_message = ""
        self.error_trace = ""

    def set_failed(self, error_message, error_trace=""):
        self.failed = True
        self.error_message = error_message
        self.error_trace = error_trace

    def to_dict(self):
        return {
            "name": self.name,
            "failed": self.failed,
            "error_msg": self.error_message,
            "error_trace": self.error_trace,
        }


class PathComponent(object):
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def to_dict(self):
        return {
            "type": self.type,
            "value": self.value,
        }


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
        self.assertions = []  # list of assertions
        self.path = []  # sample path (i.e. [package, package, module, suite, case, transaction])
        self.parent_sample = None  # pointer to parent sample

    def set_failed(self, error_msg, error_trace):
        current = self
        while current is not None:
            current.status = "FAILED"
            current.error_msg = error_msg
            current.error_trace = error_trace
            current = current.parent_sample

    def set_parent(self, parent):
        self.parent_sample = parent

    def add_subsample(self, sample):
        sample.set_parent(self)
        self.subsamples.append(sample)

    def add_assertion(self, name):
        self.assertions.append(Assertion(name))

    def set_assertion_failed(self, name, error_message, error_trace=""):
        for ass in self.assertions:
            if ass.name == name:
                ass.set_failed(error_message, error_trace)
        self.set_failed(error_message, error_trace)

    def to_dict(self):
        # type: () -> dict
        extras = copy.deepcopy(self.extras)
        if "assertions" not in extras:
            extras["assertions"] = []
        for ass in self.assertions:
            extras["assertions"].append({
                "name": ass.name,
                "isFailed": ass.failed,
                "errorMessage": ass.error_message,
            })

        return {
            "test_suite": self.test_suite,
            "test_case": self.test_case,
            "status": self.status,
            "start_time": self.start_time,
            "duration": self.duration,
            "error_msg": self.error_msg,
            "error_trace": self.error_trace,
            "extras": extras,
            "assertions": [ass.to_dict() for ass in self.assertions],
            "subsamples": [sample.to_dict() for sample in self.subsamples],
            "path": [comp.to_dict() for comp in self.path],
        }

    def __repr__(self):
        return "Sample(%r)" % self.to_dict()


class ApiritifSampleExtractor(object):
    def __init__(self):
        self.transactions_present = False
        self.active_transactions = []
        self.response_map = {}  # response -> sample

    def parse_recording(self, recording, test_case_sample):
        """

        :type recording: list[apiritif.Event]
        :type test_case_sample: Sample
        :rtype: list[Sample]
        """
        self.active_transactions.append(test_case_sample)
        for item in recording:
            if isinstance(item, apiritif.Request):
                self._parse_request(item)
            elif isinstance(item, apiritif.TransactionStarted):
                self._parse_transaction_started(item)
            elif isinstance(item, apiritif.TransactionEnded):
                self._parse_transaction_ended(item)
            elif isinstance(item, apiritif.Assertion):
                self._parse_assertion(item)
            elif isinstance(item, apiritif.AssertionFailure):
                self._parse_assertion_failure(item)
            else:
                raise ValueError("Unknown kind of event in apiritif recording: %s" % item)

        if len(self.active_transactions) != 1:
            # TODO: shouldn't we auto-balance them?
            raise ValueError("Can't parse apiritif recordings: unbalanced transactions")

        toplevel_sample = self.active_transactions.pop()

        return [toplevel_sample]

    def _parse_request(self, item):
        current_tran = self.active_transactions[-1]
        sample = Sample(
            test_suite=current_tran.test_case,
            test_case=item.address,
            status="PASSED",
            start_time=item.timestamp,
            duration=item.response.elapsed.total_seconds(),
        )
        sample.path = current_tran.path + [PathComponent("request", item.address)]
        extras = self._extract_extras(item)
        if extras:
            sample.extras.update(extras)
        self.response_map[item.response] = sample
        self.active_transactions[-1].add_subsample(sample)

    def _parse_transaction_started(self, item):
        self.transactions_present = True
        current_tran = self.active_transactions[-1]
        tran_sample = Sample(status="PASSED", test_case=item.transaction_name, test_suite=current_tran.test_case)
        tran_sample.path = current_tran.path + [PathComponent("transaction", item.transaction_name)]
        self.active_transactions.append(tran_sample)

    def _parse_transaction_ended(self, item):
        tran = item.transaction
        tran_sample = self.active_transactions.pop()
        assert tran_sample.test_case == item.transaction_name
        tran_sample.start_time = tran.start_time()
        tran_sample.duration = tran.duration()
        if tran.success is not None:
            if tran.success:
                tran_sample.status = "PASSED"
            else:
                tran_sample.status = "FAILED"
                tran_sample.error_msg = tran.error_message
        last_extras = tran_sample.subsamples[-1].extras if tran_sample.subsamples else {}
        name = tran.name
        method = last_extras.get("requestMethod") or ""
        resp_code = tran.response_code() or last_extras.get("responseCode")
        reason = last_extras.get("responseMessage") or ""
        headers = last_extras.get("requestHeaders") or {}
        response_body = tran.response() or last_extras.get("responseBody") or ""
        response_time = tran.duration() or last_extras.get("responseTime") or 0.0
        request_body = tran.request() or last_extras.get("requestBody") or ""
        request_cookies = last_extras.get("requestCookies") or {}
        request_headers = last_extras.get("requestHeaders") or {}
        extras = copy.deepcopy(tran.extras())
        extras.update(self._extras_dict(name, method, resp_code, reason, headers,
                                        response_body, len(response_body), response_time,
                                        request_body, request_cookies, request_headers))
        tran_sample.extras = extras
        self.active_transactions[-1].add_subsample(tran_sample)

    def _parse_assertion(self, item):
        sample = self.response_map.get(item.response, None)
        if sample is None:
            raise ValueError("Found assertion for unknown response")
        sample.add_assertion(item.name)

    def _parse_assertion_failure(self, item):
        sample = self.response_map.get(item.response, None)
        if sample is None:
            raise ValueError("Found assertion failure for unknown response")
        sample.set_assertion_failed(item.name, item.failure_message, "")

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
            'responseTime': int(response_time * 1000),
            'connectTime': 0,
            'latency': int(response_time * 1000),
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
