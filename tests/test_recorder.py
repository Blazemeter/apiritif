import asyncio
import sys

from asyncio import Task
from apiritif.http import _EventRecorder, Event
from tests.testcases import AsyncTestCase


class EventGenerator(Task):
    def __init__(self, recorder, index, events_count):
        self.recorder = recorder
        self.index = index
        self.events_count = events_count
        self.events = [Event(response=self.index * (i + 1)) for i in range(self.events_count)]

        super(EventGenerator, self).__init__(coro=self._record_events())

    async def _record_events(self):
        for event in self.events:
            self.recorder.record_event(event)
            await asyncio.sleep(0.1)

        self.result_events = self.recorder.pop_events(from_ts=-1, to_ts=sys.maxsize)


class TestRecorder(AsyncTestCase):
    def test_recorder_events_per_thread(self):
        recorder = _EventRecorder()
        event_generators = [EventGenerator(recorder, i, 3) for i in range(5)]

        self.run_until_complete(event_generators)

        for generator in event_generators:
            self.assertEqual(generator.events, generator.result_events)
