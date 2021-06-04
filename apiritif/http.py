"""
This is a toplevel package of Apiritif tool

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
import os
import threading
import time
from functools import wraps
from io import BytesIO

import requests
from jsonpath_ng.ext import parse as jsonpath_parse
from lxml import etree, html
from requests.structures import CaseInsensitiveDict

import apiritif
from apiritif.ssl_adapter import SSLAdapter
from apiritif.thread import get_from_thread_store, put_into_thread_store
from apiritif.utilities import *
from apiritif.utils import headers_as_text, assert_regexp, assert_not_regexp, log, get_trace

BODY_LIMIT = int(os.environ.get("APIRITIF_TRACE_BODY_EXCLIMIT", "1024"))


class TimeoutError(Exception):
    pass


class ConnectionError(Exception):
    pass


class http(object):
    log = log.getChild('http')

    @staticmethod
    def target(*args, **kwargs):
        return HTTPTarget(*args, **kwargs)

    @staticmethod
    def request(method, address, session=None,
                params=None, headers=None, cookies=None, data=None, json=None, files=None,
                encrypted_cert=None, allow_redirects=True, timeout=30):
        """

        :param method: str
        :param address: str
        :return: response
        :rtype: HTTPResponse
        """
        http.log.info("Request: %s %s", method, address)
        msg = "Request: params=%r, headers=%r, cookies=%r, data=%r, json=%r, files=%r, allow_redirects=%r, timeout=%r"
        http.log.debug(msg, params, headers, cookies, data, json, files, allow_redirects, timeout)

        if headers is None:
            headers = {}
        if "User-Agent" not in headers:
            headers["User-Agent"] = "Apiritif"

        if session is None:
            session = requests.Session()

        if encrypted_cert is not None:
            certificate_file_path, passphrase = encrypted_cert
            adapter = SSLAdapter(certificate_file_path=certificate_file_path, passphrase=passphrase)
            session.mount('https://', adapter)

        request = requests.Request(method, address,
                                   params=params, headers=headers, cookies=cookies, json=json, data=data, files=files)
        prepared = session.prepare_request(request)
        settings = session.merge_environment_settings(prepared.url, {}, False, False, None)
        try:
            response = session.send(prepared, allow_redirects=allow_redirects, timeout=timeout, **settings)
        except requests.exceptions.Timeout as exc:
            recorder.record_http_request_failure(method, address, prepared, exc, session)
            raise TimeoutError("Connection to %s timed out" % address)
        except requests.exceptions.ConnectionError as exc:
            recorder.record_http_request_failure(method, address, prepared, exc, session)
            raise ConnectionError("Connection to %s failed" % address)
        except BaseException as exc:
            recorder.record_http_request_failure(method, address, prepared, exc, session)
            raise
        http.log.info("Response: %s %s", response.status_code, response.reason)
        http.log.debug("Response headers: %r", response.headers)
        http.log.debug("Response cookies: %r", {x: response.cookies.get(x) for x in response.cookies})
        http.log.debug('Response content: \n%s', response.content)
        wrapped_response = HTTPResponse(response)
        recorder.record_http_request(method, address, prepared, wrapped_response, session)
        return wrapped_response

    @staticmethod
    def get(address, **kwargs):
        return http.request("GET", address, **kwargs)

    @staticmethod
    def post(address, **kwargs):
        return http.request("POST", address, **kwargs)

    @staticmethod
    def put(address, **kwargs):
        return http.request("PUT", address, **kwargs)

    @staticmethod
    def delete(address, **kwargs):
        return http.request("DELETE", address, **kwargs)

    @staticmethod
    def patch(address, **kwargs):
        return http.request("PATCH", address, **kwargs)

    @staticmethod
    def head(address, **kwargs):
        return http.request("HEAD", address, **kwargs)

    @staticmethod
    def options(address, **kwargs):
        return http.request("OPTIONS", address, **kwargs)

    @staticmethod
    def connect(address, **kwargs):
        return http.request("CONNECT", address, **kwargs)


class transaction(object):
    def __init__(self, name):
        self.name = name
        self.success = None  # None | True | False
        self.error_message = None
        self._request = None
        self._response = None
        self._response_code = None
        self._start_ts = None
        self._finish_ts = None
        self._extras = {}

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is not None:
            self.fail("%s: %s" % (exc_type.__name__, str(exc_value)))
        self.finish()

    def start(self, start_time=None):
        if self._start_ts is None:
            self._start_ts = start_time or time.time()
            recorder.record_transaction_start(self)

    def finish(self, end_time=None):
        if self._start_ts is None:
            raise ValueError("Can't finish non-started transaction %s" % self.name)
        if self._finish_ts is None:
            self._finish_ts = end_time or time.time()
            recorder.record_transaction_end(self)

    def finished(self):
        return self._start_ts is not None and self._finish_ts is not None

    def start_time(self):
        return self._start_ts

    def duration(self):
        if self.finished():
            return self._finish_ts - self._start_ts

    def fail(self, message=""):
        self.success = False
        self.error_message = message

    def request(self):
        return self._request

    def set_request(self, value):
        self._request = value

    def response(self):
        return self._response

    def set_response(self, value):
        self._response = value

    def response_code(self):
        return self._response_code

    def set_response_code(self, code):
        self._response_code = code

    def attach_extra(self, key, value):
        self._extras[key] = value

    def extras(self):
        return self._extras

    def __repr__(self):
        tmpl = "transaction(name=%r, success=%r)"
        return tmpl % (self.name, self.success)


class transaction_logged(transaction):
    pass


class smart_transaction(transaction_logged):
    def __init__(self, name):
        super(smart_transaction, self).__init__(name=name)
        self.driver, self.func_mode, self.controller = get_from_thread_store(("driver", "func_mode", "controller"))

        if self.controller.tran_mode:
            # as isn't first smart_transaction, we must recall init of current_sample
            self.controller.test_info["test_case"] = self.name
            self.controller.beforeTest()
        else:
            # it's first smart_transaction in test method, we shouldn't recreate current sample, just fix it
            self.controller.tran_mode = True
            self.controller.current_sample.test_case = self.name

        self.test_suite = self.controller.current_sample.test_suite

    def __enter__(self):
        super(smart_transaction, self).__enter__()
        put_into_thread_store(test_case=self.name, test_suite=self.test_suite)
        for func in apiritif.get_transaction_handlers()["enter"]:
            func(self.name, self.test_suite)  # params for compatibility, remove if bzt > 1.4.1 in cloud

        self.controller.startTest()

    def __exit__(self, exc_type, exc_val, exc_tb):
        super(smart_transaction, self).__exit__(exc_type, exc_val, exc_tb)
        self.controller.stopTest(is_transaction=True)
        message = ''

        if exc_type:
            message = str(exc_val)
            exc = exc_type, exc_val, exc_tb
            if isinstance(exc_val, AssertionError):
                status = 'failed'
                self.controller.addFailure(exc, is_transaction=True)
            else:
                status = 'broken'
                tb = get_trace(exc)
                self.controller.addError(exc_type.__name__, message, tb, is_transaction=True)

        else:
            status = 'success'
            self.controller.addSuccess(is_transaction=True)

        put_into_thread_store(status=status, message=message)
        for func in apiritif.get_transaction_handlers()["exit"]:
            func(status, message)  # params for compatibility, remove if bzt > 1.4.1 in cloud

        self.controller.afterTest(is_transaction=True)

        return not self.func_mode  # don't reraise in load mode


class Event(object):
    def __init__(self, response=None):
        self.timestamp = time.time()
        self.response = response

    def to_dict(self):  # supposed to be overridden by extenders
        return {}


class Request(Event):
    def __init__(self, method, address, request, response, session):
        """
        :type method: str
        :type address: str
        :type request: requests.PreparedRequest
        :type response: HTTPResponse
        :type session: requests.Session
        """
        super(Request, self).__init__(response)
        self.method = method
        self.address = address
        self.request = request
        self.session = session

    def __repr__(self):
        return "Request(method=%r, address=%r)" % (self.method, self.address)


class RequestFailure(Request):
    def __init__(self, method, address, request, exc, session):
        """

        :type method: str
        :type address: str
        :type request: requests.PreparedRequest
        :type exc: BaseException
        :type session: requests.Session
        """
        response = requests.Response()
        response.request = request
        response.status_code = 999
        response._content = ""

        super(RequestFailure, self).__init__(method, address, request, HTTPResponse(response), session)
        self.method = method
        self.address = address
        self.request = request
        self.exception = exc
        self.session = session

    def __repr__(self):
        return "RequestFailure(method=%r, address=%r)" % (self.method, self.address)


class TransactionStarted(Event):
    def __init__(self, transaction):
        super(TransactionStarted, self).__init__(None)
        self.transaction = transaction
        self.transaction_name = transaction.name

    def __repr__(self):
        return "TransactionStarted(transaction_name=%r)" % self.transaction_name


class TransactionEnded(Event):
    def __init__(self, transaction):
        super(TransactionEnded, self).__init__()
        self.transaction = transaction
        self.transaction_name = transaction.name

    def __repr__(self):
        return "TransactionEnded(transaction_name=%r)" % self.transaction_name


class Assertion(Event):
    def __init__(self, name, response, extras):
        super(Assertion, self).__init__(response)
        self.name = name
        self.extras = extras

    def __repr__(self):
        return "Assertion(name=%r)" % self.name


class AssertionFailure(Event):
    def __init__(self, assertion_name, response, failure_message):
        super(AssertionFailure, self).__init__(response)
        self.name = assertion_name
        self.failure_message = failure_message

    def __repr__(self):
        return "Assertion(name=%r, failure_message=%r)" % (self.name, self.failure_message)


class _EventRecorder(object):
    local = threading.local()

    def __init__(self):
        self.log = log.getChild('recorder')
        self.log.debug("Creating recorder")

    def get_recording(self):
        rec = getattr(self.local, 'recording', None)
        if rec is None:
            self.local.recording = []
        return self.local.recording

    def pop_events(self, from_ts, to_ts):
        recording = self.get_recording()
        collected = []
        new_recording = []
        for event in recording:
            if from_ts <= event.timestamp <= to_ts:
                collected.append(event)
            else:
                new_recording.append(event)
        del recording[:]
        recording.extend(new_recording)
        return collected

    def record_event(self, event):
        self.log.debug("Recording event %r", event)
        recording = self.get_recording()
        recording.append(event)

    def record_transaction_start(self, tran):
        self.record_event(TransactionStarted(tran))
        if isinstance(tran, transaction_logged):
            self.log.info(u"Transaction started:: start_time=%.3f,name=%s", tran.start_time(), tran.name)

    def record_transaction_end(self, tran):
        self.record_event(TransactionEnded(tran))
        if isinstance(tran, transaction_logged):
            self.log.info(u"Transaction ended:: duration=%.3f,name=%s", tran.duration(), tran.name)

    def record_http_request(self, method, address, request, response, session):
        self.record_event(Request(method, address, request, response, session))

    def record_http_request_failure(self, method, address, request, exception, session):
        failure = RequestFailure(method, address, request, exception, session)
        self.record_event(failure)

    def record_assertion(self, assertion_name, target_response, extras):
        self.record_event(Assertion(assertion_name, target_response, extras))

    def record_assertion_failure(self, assertion_name, target_response, failure_message):
        self.record_event(AssertionFailure(assertion_name, target_response, failure_message))

    @staticmethod
    def assertion_decorator(assertion_method):
        @wraps(assertion_method)
        def _impl(self, *method_args, **method_kwargs):
            assertion_name = getattr(assertion_method, '__name__', 'assertion')
            extras = {"args": list(method_args), "kwargs": method_kwargs}
            recorder.record_assertion(assertion_name, self, extras)
            try:
                return assertion_method(self, *method_args, **method_kwargs)
            except BaseException as exc:
                recorder.record_assertion_failure(assertion_name, self, str(exc))
                raise

        return _impl


recorder = _EventRecorder()


class HTTPTarget(object):
    def __init__(self,
                 address,
                 base_path=None,
                 use_cookies=True,
                 additional_headers=None,
                 keep_alive=True,
                 auto_assert_ok=True,
                 timeout=30,
                 allow_redirects=True,
                 session=None,
                 cert=None,
                 encrypted_cert=None):
        self.address = address
        # config flags
        self._base_path = base_path
        self._use_cookies = use_cookies
        self._keep_alive = keep_alive
        self._additional_headers = additional_headers or {}
        self._auto_assert_ok = auto_assert_ok
        self._timeout = timeout
        self._allow_redirects = allow_redirects
        # internal vars
        self.__session = session

    def use_cookies(self, use=True):
        self._use_cookies = use
        return self

    def base_path(self, base_path):
        self._base_path = base_path
        return self

    def keep_alive(self, keep=True):
        self._keep_alive = keep
        return self

    def additional_headers(self, headers):
        self._additional_headers.update(headers)
        return self

    def auto_assert_ok(self, value=True):
        self._auto_assert_ok = value
        return self

    def timeout(self, value):
        self._timeout = value
        return self

    def allow_redirects(self, value=True):
        self._allow_redirects = value
        return self

    def _bake_address(self, path):
        addr = self.address
        if self._base_path is not None:
            addr += self._base_path
        addr += path
        return addr

    def request(self, method, path,
                params=None, headers=None, cookies=None, data=None, json=None, files=None,
                allow_redirects=None, timeout=None):
        """
        Prepares and sends an HTTP request. Returns the HTTPResponse object.

        :param method: str
        :param path: str
        :return: response
        :rtype: HTTPResponse
        """
        headers = headers or {}
        timeout = timeout if timeout is not None else self._timeout
        allow_redirects = allow_redirects if allow_redirects is not None else self._allow_redirects

        if self._keep_alive and self.__session is None:
            self.__session = requests.Session()

        if self.__session is not None and not self._use_cookies:
            self.__session.cookies.clear()

        address = self._bake_address(path)
        req_headers = copy.deepcopy(self._additional_headers)
        req_headers.update(headers)

        response = http.request(method, address, session=self.__session,
                                params=params, headers=req_headers, cookies=cookies, data=data, json=json, files=files,
                                allow_redirects=allow_redirects, timeout=timeout)
        if self._auto_assert_ok:
            response.assert_ok()
        return response

    def get(self, path, **kwargs):
        # TODO: how to reuse requests.session? - pass it as additional parameter for http.request ?
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def head(self, path, **kwargs):
        return self.request("HEAD", path, **kwargs)

    def options(self, path, **kwargs):
        return self.request("OPTIONS", path, **kwargs)

    def connect(self, path, **kwargs):
        return self.request("CONNECT", path, **kwargs)


class HTTPResponse(object):
    def __init__(self, py_response):
        """
        Construct HTTPResponse from requests.Response object

        :type py_response: requests.Response
        """
        self.url = py_response.url
        self.method = py_response.request.method
        self.status_code = int(py_response.status_code)
        self.reason = py_response.reason

        self.headers = CaseInsensitiveDict(py_response.headers)
        self.cookies = {x: py_response.cookies.get(x) for x in py_response.cookies}

        self.text = py_response.text
        self.content = py_response.content

        self.elapsed = py_response.elapsed

        self._response = py_response
        self._request = py_response.request

    def json(self):
        return self._response.json()

    def __eq__(self, other):
        """
        :type other: HTTPResponse
        """
        return isinstance(other, self.__class__) \
               and self.status_code == other.status_code \
               and self.method == other.method \
               and self.url == other.url \
               and self.reason == other.reason \
               and self.headers == other.headers \
               and self.cookies == other.cookies \
               and self.text == other.text \
               and self.content == other.content

    def __hash__(self):
        return hash((self.url, self.method, self.status_code, self.reason, self.text, self.content))

    def __repr__(self):
        params = (self.method, self.url, self.status_code, self.reason)
        return "%s %s => %s %s" % params

    @recorder.assertion_decorator
    def assert_ok(self, msg=None):
        if self.status_code >= 400:
            msg = msg or "Request to %s didn't succeed (%s)" % (self.url, self.status_code)
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_failed(self, msg=None):
        if self.status_code < 400:
            msg = msg or "Request to %s didn't fail (%s)" % (self.url, self.status_code)
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_2xx(self, msg=None):
        if not 200 <= self.status_code < 300:
            msg = msg or "Response code isn't 2xx, it's %s" % self.status_code
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_3xx(self, msg=None):
        if not 300 <= self.status_code < 400:
            msg = msg or "Response code isn't 3xx, it's %s" % self.status_code
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_4xx(self, msg=None):
        if not 400 <= self.status_code < 500:
            msg = msg or "Response code isn't 4xx, it's %s" % self.status_code
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_5xx(self, msg=None):
        if not 500 <= self.status_code < 600:
            msg = msg or "Response code isn't 5xx, it's %s" % self.status_code
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_status_code(self, code, msg=None):
        actual = str(self.status_code)
        expected = str(code)
        if actual != expected:
            msg = msg or "Actual status code (%s) didn't match expected (%s)" % (actual, expected)
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_status_code_in(self, codes, msg=None):
        actual = str(self.status_code)
        expected = [str(code) for code in codes]
        if actual not in expected:
            msg = msg or "Actual status code (%s) is not one of expected expected (%s)" % (actual, expected)
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_not_status_code(self, code, msg=None):
        actual = str(self.status_code)
        expected = str(code)
        if actual == expected:
            msg = msg or "Actual status code (%s) unexpectedly matched" % actual
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_in_body(self, member, msg=None):
        if member not in self.text:
            msg = msg or "%r wasn't found in response body" % member
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_not_in_body(self, member, msg=None):
        if member in self.text:
            msg = msg or "%r was found in response body" % member
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_regex_in_body(self, regex, match=False, msg=None):
        assert_regexp(regex, self.text, match=match, msg=msg)
        return self

    @recorder.assertion_decorator
    def assert_regex_not_in_body(self, regex, match=False, msg=None):
        assert_not_regexp(regex, self.text, match=match, msg=msg)
        return self

    # TODO: assert_content_type?

    @recorder.assertion_decorator
    def assert_has_header(self, header, msg=None):
        if header not in self.headers:
            msg = msg or "Header %s wasn't found in response headers: %r" % (header, self.headers)
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_header_value(self, header, value, msg=None):
        self.assert_has_header(header)
        actual = self.headers[header]
        if actual != value:
            msg = msg or "Actual header value (%r) isn't equal to expected (%r)" % (actual, value)
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_in_headers(self, member, msg=None):
        headers_text = headers_as_text(self.headers)
        if member not in headers_text:
            msg = msg or "Header %s wasn't found in response headers text: %r" % (member, headers_text)
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_not_in_headers(self, member, msg=None):
        if member in headers_as_text(self.headers):
            msg = msg or "Header %s was found in response headers text" % member
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_regex_in_headers(self, member, msg=None):
        assert_regexp(member, headers_as_text(self.headers), msg=msg)
        return self

    @recorder.assertion_decorator
    def assert_regex_not_in_headers(self, member, msg=None):
        assert_not_regexp(member, headers_as_text(self.headers), msg=msg)
        return self

    @recorder.assertion_decorator
    def assert_jsonpath(self, jsonpath_query, expected_value=None, msg=None):
        jsonpath_expr = jsonpath_parse(jsonpath_query)
        body = self.json()
        matches = jsonpath_expr.find(body)
        if not matches:
            msg = msg or "JSONPath query %r didn't match response: %s" % (jsonpath_query, self.text[:BODY_LIMIT])
            raise AssertionError(msg)
        actual_value = matches[0].value
        if expected_value is not None and actual_value != expected_value:
            tmpl = "Actual value at JSONPath query (%r) isn't equal to expected (%r)"
            msg = msg or tmpl % (actual_value, expected_value)
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_not_jsonpath(self, jsonpath_query, msg=None):
        jsonpath_expr = jsonpath_parse(jsonpath_query)
        body = self.json()
        matches = jsonpath_expr.find(body)
        if matches:
            msg = msg or "JSONPath query %r did match response: %s" % (jsonpath_query, self.text[:BODY_LIMIT])
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_xpath(self, xpath_query, parser_type='html', validate=False, msg=None):
        parser = etree.HTMLParser() if parser_type == 'html' else etree.XMLParser(dtd_validation=validate)
        tree = etree.parse(BytesIO(self.content), parser)
        matches = tree.xpath(xpath_query)
        if not matches:
            msg = msg or "XPath query %r didn't match response content: %s" % (xpath_query, self.text[:BODY_LIMIT])
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_not_xpath(self, xpath_query, parser_type='html', validate=False, msg=None):
        parser = etree.HTMLParser() if parser_type == 'html' else etree.XMLParser(dtd_validation=validate)
        tree = etree.parse(BytesIO(self.content), parser)
        matches = tree.xpath(xpath_query)
        if matches:
            msg = msg or "XPath query %r did match response content: %s" % (xpath_query, self.text[:BODY_LIMIT])
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_cssselect(self, query, expected_value=None, attribute=None, msg=None):
        tree = html.fromstring(self.text)
        q = tree.cssselect(query)
        vals = [(x.text if attribute is None else x.attrib[attribute]) for x in q]

        matches = expected_value in vals if expected_value is not None else vals
        if not matches:
            msg = msg or "CSSSelect query %r didn't match response content: %s" % (query, self.text[:BODY_LIMIT])
            raise AssertionError(msg)
        return self

    @recorder.assertion_decorator
    def assert_not_cssselect(self, query, expected_value=None, attribute=None, msg=None):
        try:
            self.assert_cssselect(query, expected_value, attribute)
        except AssertionError:
            return self

        msg = msg or "CSSSelect query %r did match response content: %s" % (query, self.text[:BODY_LIMIT])
        raise AssertionError(msg)

    # TODO: assertTiming? to assert response time / connection time

    def extract_regex(self, regex, default=None):
        extracted_value = default
        for item in re.finditer(regex, self.text):
            extracted_value = item
            break
        return extracted_value

    def extract_jsonpath(self, jsonpath_query, default=None):
        jsonpath_expr = jsonpath_parse(jsonpath_query)
        body = self.json()
        matches = jsonpath_expr.find(body)
        if not matches:
            return default
        return matches[0].value

    def extract_cssselect(self, selector, attribute=None, default=None):
        tree = html.fromstring(self.text)
        q = tree.cssselect(selector)
        matches = [(x.text if attribute is None else x.attrib[attribute]) for x in q]

        if not matches:
            return default
        return matches[0]

    def extract_xpath(self, xpath_query, default=None, parser_type='html', validate=False):
        parser = etree.HTMLParser() if parser_type == 'html' else etree.XMLParser(dtd_validation=validate)
        tree = etree.parse(BytesIO(self.content), parser)
        matches = tree.xpath(xpath_query)
        if not matches:
            return default
        match = matches[0]
        return match.text
