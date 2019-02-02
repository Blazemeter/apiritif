"""
Data feeders for Apiritif.

Copyright 2018 BlazeMeter Inc.

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
import threading
import unicodecsv as csv
from itertools import cycle, islice
from apiritif.local import thread_indexes


storage = threading.local()


class CSVReader(object):
    def __init__(self, filename):
        self.step, self.first = thread_indexes()
        self.csv = None
        self.fds = open(filename, 'rb')
        self.reader = cycle(csv.DictReader(self.fds, encoding='utf-8'))

    def close(self):
        if self.fds is not None:
            self.fds.close()
        self.reader = None

    def read_vars(self):
        if not getattr(self, "reader", None):
            return      # todo: exception?

        if not self.csv:    # first element
            self.csv = next(islice(self.reader, self.first, self.first + 1))
        else:               # next one
            self.csv = next(islice(self.reader, self.step - 1, self.step))


class CSVFeeder(object):
    def __init__(self, filename):
        self.filename = filename

    def close(self):
        if getattr(storage, "reader", None) is not None:
            storage.reader.close()

    def read_vars(self):
        if getattr(storage, "reader", None) is None:   # the first call in the thread
            storage.reader = CSVReader(self.filename)

        storage.reader.read_vars()

    @staticmethod
    def get_vars():
        if getattr(storage, "reader", None) is not None:
            return storage.reader.csv

