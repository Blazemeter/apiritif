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
import threading
import os

import unicodecsv as csv
from itertools import cycle, islice

from apiritif.utils import NormalShutdown
from apiritif.local import thread_indexes

storage = threading.local()


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
    def __init__(self, filename, loop=True):
        self.storage = threading.local()
        self.filename = filename
        self.loop = loop

    def open(self):
        self.storage.fds = open(self.filename, 'rb')
        self.storage.reader = cycle(csv.DictReader(self.storage.fds, encoding='utf-8'))
        self.storage.csv = None
        self.storage.step, self.storage.first = thread_indexes()  # TODO: maybe use constructor fields

    def close(self):
        if self.storage.fds is not None:
            self.storage.fds.close()
        self.storage.reader = None

    def read_vars(self):
        if not getattr(self.storage, "reader", None):
            self.open()

        if not getattr(self.storage, "reader", None):
            return      # todo: exception?

        if not self.storage.csv:    # first element
            self.storage.csv = next(islice(self.storage.reader, self.storage.first, self.storage.first + 1))
        else:               # next one
            self.storage.csv = next(islice(self.storage.reader, self.storage.step - 1, self.storage.step))

    def get_vars(self):
        return self.storage.csv

