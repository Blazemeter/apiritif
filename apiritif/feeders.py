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
import abc
import unicodecsv as csv


class Feeder(abc.ABC):
    def __init__(self, vars):
        self.vars = vars

    @abc.abstractmethod
    def open(self):
        pass

    @abc.abstractmethod
    def next(self):
        pass


class CSVFeeder(Feeder):
    def __init__(self, filename, vars):
        super(CSVFeeder, self).__init__(vars)
        self.filename = filename
        self.fds = None
        self.reader = None

    def open(self):
        self.fds = open(self.filename, 'rb')
        self.reader = csv.DictReader(self.fds, encoding='utf-8')
        self.next()

    def close(self):
        if self.fds is not None:
            self.fds.close()
        self.reader = None

    def next(self):
        try:
            items = next(self.reader)
        except StopIteration:
            self.close()
            self.open()
            return self.next()

        for key, value in items.items():
            self.vars[key] = value
