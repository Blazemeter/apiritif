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
import os
import threading

import unicodecsv as csv


class Feeder(object):
    instances = []

    def __init__(self, vars):
        self.vars = vars
        Feeder.instances.append(self)

    @abc.abstractmethod
    def open(self):
        pass

    @abc.abstractmethod
    def step(self):
        pass

    @classmethod
    def step_all_feeders(cls):
        print('pid=%d, tid=%d, step_all_feeders' % (os.getpid(), threading.get_ident()))
        for instance in cls.instances:
            instance.step()


class CSVFeeder(Feeder):
    def __init__(self, filename, vars, open=True):
        super(CSVFeeder, self).__init__(vars)
        self.filename = filename
        self.fds = None
        self.reader = None
        if open:
            self.open()
        # TODO: 'loop' flag

    def open(self):
        self.fds = open(self.filename, 'rb')
        self.reader = csv.DictReader(self.fds, encoding='utf-8')

    def reopen(self):
        if self.fds is not None:
            self.fds.seek(0)
            self.reader = csv.DictReader(self.fds, encoding='utf-8')

    def close(self):
        if self.fds is not None:
            self.fds.close()
        self.reader = None

    def step(self):
        print('stepping csv feeder')
        try:
            items = next(self.reader)
        except StopIteration:
            self.reopen()
            return self.step()

        for key, value in items.items():
            self.vars[key] = value
