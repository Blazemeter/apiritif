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


def set_index(index):
    _thread_local.index = index


def get_index():
    return _thread_local.index


def set_total(total):
    global _total
    _total = total


def get_total():
    global _total
    return _total


def add_reader(feeder_id, reader):
    readers = getattr(_thread_local, "readers", None)
    if not readers:
        _thread_local.readers = {}

    feeders = _thread_local.readers.keys()
    if feeder_id not in feeders:
        _thread_local.readers[feeder_id] = []

    _thread_local.readers[feeder_id].append(reader)


def get_readers(feeder_id=None):
    result = []

    readers = getattr(_thread_local, "readers", {})
    if not readers:
        return result

    if feeder_id is None:
        ids = readers.keys()
    else:
        ids = [feeder_id]

    for feeder in ids:
        result.extend(_thread_local.readers.get(feeder, []))

    return result
