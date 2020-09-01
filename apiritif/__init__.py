
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

from .csv import CSVReaderPerThread
from .thread import put_into_thread_store, get_from_thread_store, external_log
from .thread import get_transaction_handlers, set_transaction_handlers, get_iteration
from .thread import get_logging_handlers, set_logging_handlers
from .http import http, transaction, transaction_logged, smart_transaction, recorder
from .http import Event, TransactionStarted, TransactionEnded, Request, Assertion, AssertionFailure
from .utilities import *
from .utils import headers_as_text, assert_regexp, assert_not_regexp, log
