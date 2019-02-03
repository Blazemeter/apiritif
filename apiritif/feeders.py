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
import unicodecsv as csv
from itertools import cycle, islice
from .thread import get_total, get_index, get_readers, add_reader


class CSVReader(object):
    def __init__(self, filename):
        self.step = get_total()
        self.first = get_index()
        self.csv = {}
        self.fds = open(filename, 'rb')
        self._reader = cycle(csv.DictReader(self.fds, encoding='utf-8'))

    def close(self):
        if self.fds is not None:
            self.fds.close()
        self._reader = None

    def read_vars(self):
        if not self._reader:
            return      # todo: exception?

        if not self.csv:    # first element
            self.csv = next(islice(self._reader, self.first, self.first + 1))
        else:               # next one
            self.csv = next(islice(self._reader, self.step - 1, self.step))


class CSVFeeder(object):
    def __init__(self, config):
        if not isinstance(config, dict):
            config = [config]

        self.config = config

    def _set_readers(self):
        for reader_cfg in self.config:
            add_reader(id(self), CSVReader(reader_cfg))

    def read_vars(self):
        readers = get_readers(id(self))
        if not readers:
            self._set_readers()

        for reader in get_readers(id(self)):    # revise readers
            reader.read_vars()

    def close(self):
        readers = get_readers(id(self))
        while readers:
            readers.pop().close()

    def get_vars(self):
        result = {}
        readers = get_readers(id(self))
        for reader in readers:
            result.update(reader.csv)

        return result
