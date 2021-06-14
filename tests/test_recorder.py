import threading
import time
import sys

from unittest import TestCase
from apiritif.http import _EventRecorder, Event


class EventGenerator(threading.Thread):
    def __init__(self, recorder, index, events_count):
        self.recorder = recorder
        self.index = index
        self.events_count = events_count
        self.events = [Event(response=self.index * (i + 1)) for i in range(self.events_count)]

        super(EventGenerator, self).__init__(target=self._record_events)

    def _record_events(self):
        for event in self.events:
            self.recorder.record_event(event)
            time.sleep(0.1)

        self.result_events = self.recorder.pop_events(from_ts=-1, to_ts=sys.maxsize)


class TestRecorder(TestCase):

    # _EventRecorder class have to store separate events for separate thread.
    # Here each fake thread (EventGenerator) generate an event for common recorder.
    # Then each thread read this event from this recorder with some delay.
    # As the result written and read events should be the same.
    def test_recorder_events_per_thread(self):
        recorder = _EventRecorder()
        event_generators = [EventGenerator(recorder, i, 3) for i in range(5)]

        for generator in event_generators:
            generator.start()
        for generator in event_generators:
            generator.join()
        for generator in event_generators:
            self.assertEqual(generator.events, generator.result_events)
