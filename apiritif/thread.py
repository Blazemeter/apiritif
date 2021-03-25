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
from contextvars import ContextVar


class ContextVariables:
    index = ContextVar('index')
    iteration = ContextVar('iteration')
    args = ContextVar('args')
    kwargs = ContextVar('kwargs')
    transaction_handlers = ContextVar('transaction_handlers')
    log_handlers = ContextVar('log_handlers')


_total = 1


def set_total(total):
    global _total
    _total = total


def get_total():
    global _total
    return _total


def set_index(value):
    ContextVariables.index.set(value)


def get_index():
    return ContextVariables.index.get(0)


def set_iteration(value):
    ContextVariables.iteration.set(value)


def get_iteration():
    return ContextVariables.iteration.get(0)


def put_into_thread_store(*args, **kwargs):
    if args:
        ContextVariables.args.set(args)
    if kwargs:
        current_kwargs = ContextVariables.kwargs.get({})
        current_kwargs.update(kwargs)
        ContextVariables.kwargs.set(current_kwargs)


def get_from_thread_store(names=None):
    current_kwargs = ContextVariables.kwargs.get(None)
    if names and current_kwargs:
        only_one = False
        if isinstance(names, str):
            names = [names]
            only_one = True
        kwargs = [current_kwargs.get(key) for key in names]
        if only_one:
            return kwargs[0]
        else:
            return kwargs

    else:
        current_args = ContextVariables.args.get(None)
        if current_args:
            return current_args


def get_transaction_handlers():
    return ContextVariables.transaction_handlers.get()


def clean_transaction_handlers():
    handlers = {'enter': [], 'exit': []}
    ContextVariables.transaction_handlers.set(handlers)


def set_transaction_handlers(handlers):
    ContextVariables.transaction_handlers.set(handlers)


def external_log(log_line):
    for func in get_logging_handlers():
        func(log_line)


def set_logging_handlers(handlers):
    ContextVariables.log_handlers.set(handlers)


def get_logging_handlers():
    return ContextVariables.log_handlers.get()


def clean_logging_handlers():
    ContextVariables.log_handlers.set([])
