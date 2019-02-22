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
    _thread_local.args = args
    _thread_local.kwargs = kwargs


def get_from_thread_store(names=None):
    if names and getattr(_thread_local, "kwargs"):
        return [_thread_local.kwargs[key] for key in names]
    elif getattr(_thread_local, "args"):
        return _thread_local.args
