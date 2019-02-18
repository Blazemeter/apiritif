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

import apiritif.thread as thread
from apiritif.utils import NormalShutdown

thread_data = threading.local()


class Reader(object):
    def read_vars(self):
        pass

    def get_vars(self):
        pass

    def close(self):
        pass


class CSVReaderPerThread(Reader):  # processes multi-thread specific
    def __init__(self, filename, fieldnames=None, delimiter=None, loop=True, quoted=False):
        self.filename = filename
        self.fieldnames = fieldnames
        self.delimiter = delimiter
        self.loop = loop
        self.quoted = quoted

    def _get_csv_reader(self, create=False):
        csv_readers = getattr(thread_data, "csv_readers", None)
        if not csv_readers:
            thread_data.csv_readers = {}

        csv_reader = thread_data.csv_readers.get(id(self))
        if not csv_reader and create:
            csv_reader = CSVReader(
                filename=self.filename,
                fieldnames=self.fieldnames,
                step=thread.get_total(),
                first=thread.get_index(),
                delimiter=self.delimiter,
                loop=self.loop,
                quoted=self.quoted)

            thread_data.csv_readers[id(self)] = csv_reader

        return csv_reader

    def read_vars(self):
        self._get_csv_reader(create=True).read_vars()

    def close(self):
        csv_reader = self._get_csv_reader()
        if csv_reader:
            del thread_data.csv_readers[id(self)]
            csv_reader.close()

    def get_vars(self):
        csv_reader = self._get_csv_reader()
        if csv_reader:
            return csv_reader.get_vars()
        else:
            return {}


class CSVReader(Reader):
    def __init__(self, filename, step=1, first=0, fieldnames=None, delimiter=None, loop=True, quoted=False):
        self.step = step
        self.first = first
        self.csv = {}
        self.fds = open(filename, 'rb')

        format_params = {}
        if delimiter:
            format_params["delimiter"] = delimiter

        format_params["quoting"] = csv.QUOTE_MINIMAL if quoted else csv.QUOTE_NONE

        self._reader = csv.DictReader(self.fds, encoding='utf-8', fieldnames=fieldnames, **format_params)
        if loop:
            self._reader = cycle(self._reader)

    def close(self):
        if self.fds is not None:
            self.fds.close()
        self._reader = None

    def read_vars(self):
        if not self._reader:
            return  # todo: exception?

        try:
            if not self.csv:  # first element
                self.csv = next(islice(self._reader, self.first, self.first + 1))
            else:  # next one
                self.csv = next(islice(self._reader, self.step - 1, self.step))
        except StopIteration:
            stop_reason = "Data source is exhausted: %s" % self.fds.name
            raise NormalShutdown(stop_reason)  # Just send it up

    def get_vars(self):
        return self.csv
