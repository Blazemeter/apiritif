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

                extras = {}
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
