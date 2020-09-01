"""

Copyright 2019 BlazeMeter Inc.

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
from threading import local


_total = 1
_thread_local = local()


def set_total(total):
    global _total
    _total = total


def get_total():
    global _total
    return _total


def set_index(index):
    _thread_local.index = index


def get_index():
    index = getattr(_thread_local, "index", 0)
    return index


def set_iteration(iteration):
    _thread_local.iteration = iteration


def get_iteration():
    iteration = getattr(_thread_local, "iteration", 0)
    return iteration


def put_into_thread_store(*args, **kwargs):
    if args:
        _thread_local.args = args
    if kwargs:
        current_kwargs = getattr(_thread_local, "kwargs", {})
        current_kwargs.update(kwargs)
        _thread_local.kwargs = current_kwargs


def get_from_thread_store(names=None):
    if names and hasattr(_thread_local, "kwargs"):
        only_one = False
        if isinstance(names, str):
            names = [names]
            only_one = True
        kwargs = [_thread_local.kwargs.get(key) for key in names]
        if only_one:
            return kwargs[0]
        else:
            return kwargs

    elif hasattr(_thread_local, "args"):
        return _thread_local.args


def get_transaction_handlers():
    transaction_handlers = get_from_thread_store('transaction_handlers')
    return transaction_handlers


def clean_transaction_handlers():
    handlers = {'enter': [], 'exit': []}
    _thread_local.kwargs["transaction_handlers"] = handlers


def set_transaction_handlers(handlers):
    put_into_thread_store(transaction_handlers=handlers)


def external_log(log_line):
    for func in get_logging_handlers():
        func(log_line)


def set_logging_handlers(handlers):
    put_into_thread_store(log_handlers=handlers)


def get_logging_handlers():
    log_handlers = get_from_thread_store("log_handlers")
    return log_handlers


def clean_logging_handlers():
    _thread_local.kwargs["log_handlers"] = []
