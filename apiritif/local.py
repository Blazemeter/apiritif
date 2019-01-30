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


_thread_local = local()


def thread_indexes(total=None, index=None):
    initialized = getattr(_thread_local, 'initialized', None)
    if initialized is None:
        _thread_local.initialized = True
        _thread_local.total = 1
        _thread_local.index = 0

    if total is not None:
        _thread_local.total = total

    if index is not None:
        _thread_local.index = index

    return _thread_local.total, _thread_local.index
