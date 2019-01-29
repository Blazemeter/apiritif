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
from itertools import cycle, islice

from apiritif.utils import NormalShutdown
from apiritif.loadgen import local_data


class Feeder(object):
    instances = []

    def __init__(self, vars_dict, register=True):
        self.vars_dict = vars_dict
        if register:
            Feeder.instances.append(self)

    @abc.abstractmethod
    def open(self):
        pass

    @abc.abstractmethod
    def step(self):
        pass

    @classmethod
    def step_all_feeders(cls):
        for instance in cls.instances:
            instance.step()


class CSVFeeder(object):
    def __init__(self, filename, loop=True, auto_open=True):
        self.filename = filename
        self.size = None
        self.fds = None
        self.reader = None
        self.loop = loop
        if auto_open:
            self.open()

    def open(self):
        self.fds = open(self.filename, 'rb')
        self.reader = cycle(csv.DictReader(self.fds, encoding='utf-8'))
        local_data.csv = None

    def get(self, n):
        if not self.fds:
            self.open()
        if not self.size:
            raise StopIteration()
        pos = n % self.size
        self.fds.seek(pos)
        return next(self.fds)

    def reopen(self):
        if self.fds is not None:
            self.fds.seek(0)
            self.reader = csv.DictReader(self.fds, encoding='utf-8')

    def close(self):
        if self.fds is not None:
            self.fds.close()
        self.reader = None

    def step(self):
        try:
            items = next(self.reader)
        except StopIteration:
            if not self.loop:
                raise NormalShutdown("CSV file exhausted")
            self.reopen()
            return self.step()

    # def __init__(self, fname, index=0, step=1):
    #     # todo: fill fields
    #     super(CSVFeeder, self).__init__()

    def read_vars(self):
        step = local_data.total_concurrency
        first = local_data.thread_index

        if not local_data.csv:
            local_data.csv = next(islice(self.reader, first, first + 1))
        else:
            local_data.csv = next(islice(self.reader, step - 1, step))

    def get_vars(self):
        return local_data.csv

    @classmethod
    def get_local_feeder(cls, index=0, count=1, loop=True):
        # fname?
        # todo: implement it
        pass