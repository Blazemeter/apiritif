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

import os

from threading import local


a = 0
thread_local = local()


def thread_indexes(total=None, index=None):
    global a
    print("%s [%s]" % (a, os.getpid()))
    a = a + 1
    initialized = getattr(thread_local, 'initialized', None)
    if initialized is None:
        thread_local.initialized = True
        thread_local.total = 1
        thread_local.index = 0
        print("Initializing thread_local %s" % os.getpid())
    elif total or index:
        a = 1+ 1
        print("WTF? %s" % os.getpid())
    else:
        print("Read thread_local %s" % os.getpid())

    if total is not None:
        thread_local.total = total

    if index is not None:
        thread_local.index = index

    return thread_local.total, thread_local.index