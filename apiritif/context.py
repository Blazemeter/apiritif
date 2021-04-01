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
import warnings


class ContextVariables:
    def __init__(self):
        self.index = ContextVar('index')
        self.iteration = ContextVar('iteration')
        self.args = ContextVar('args')
        self.kwargs = ContextVar('kwargs')
        self.transaction_handlers = ContextVar('transaction_handlers')
        self.log_handlers = ContextVar('log_handlers')


context_variables = ContextVariables()

_total = 1


def set_total(total):
    global _total
    _total = total


def get_total():
    global _total
    return _total


def set_index(value):
    context_variables.index.set(value)


def get_index():
    return context_variables.index.get(0)


def set_iteration(value):
    context_variables.iteration.set(value)


def get_iteration():
    return context_variables.iteration.get(0)


def save_to_context(*args, **kwargs):
    if args:
        context_variables.args.set(args)
    if kwargs:
        current_kwargs = context_variables.kwargs.get({})
        current_kwargs.update(kwargs)
        context_variables.kwargs.set(current_kwargs)


def put_into_thread_store(*args, **kwargs):
    warnings.warn('`put_into_thread_store` function is deprecated. Use `put_into_thread_store` instead', DeprecationWarning)
    save_to_context(*args, **kwargs)


def get_from_context(names=None):
    current_kwargs = context_variables.kwargs.get(None)
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
        current_args = context_variables.args.get(None)
        if current_args:
            return current_args


def get_from_thread_store(names=None):
    warnings.warn('`get_from_thread_store` function is deprecated. Use `get_from_context` instead', DeprecationWarning)
    return get_from_context(names)


def get_transaction_handlers():
    return context_variables.transaction_handlers.get()


def clean_transaction_handlers():
    handlers = {'enter': [], 'exit': []}
    context_variables.transaction_handlers.set(handlers)


def set_transaction_handlers(handlers):
    context_variables.transaction_handlers.set(handlers)


def external_log(log_line):
    for func in get_logging_handlers():
        func(log_line)


def set_logging_handlers(handlers):
    context_variables.log_handlers.set(handlers)


def get_logging_handlers():
    return context_variables.log_handlers.get()


def clean_logging_handlers():
    context_variables.log_handlers.set([])
