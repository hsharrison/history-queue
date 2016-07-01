import os
from collections import namedtuple
import asyncio
from unittest import TestCase
from toolz import complement
import pytest
from hypothesis import given, settings, Verbosity
import hypothesis.strategies as st
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, precondition

from hqueue import HistoryQueue

settings.register_profile('ci', settings(max_examples=1000, stateful_step_count=200, strict=True))
settings.register_profile('debug', settings(max_examples=10, verbosity=Verbosity.verbose))
settings.load_profile(os.getenv('HYPOTHESIS_PROFILE', 'default'))

ReceivedItem = namedtuple('ReceivedItem', ('n_previously_received', 'item'))


def anything():
    return st.one_of(
        st.integers(),
        st.text(),
        st.tuples(st.integers(), st.text()),
    )


def preconditions(*conditions):
    def combined_condition(self):
        return all(condition(self) for condition in conditions)
    return precondition(combined_condition)


class HQRules(RuleBasedStateMachine):
    items_received = Bundle('received items')

    def __init__(self):
        super().__init__()
        self.items_added = []
        self.n_items_received = 0
        self.hq = None

    @property
    def n_items_added(self):
        return len(self.items_added)

    def has_hq(self):
        return self.hq is not None

    def backlog_is_empty(self):
        return self.n_items_received == self.n_items_added

    def backlog_is_too_full(self):
        return (
            self.has_hq() and
            self.hq.max_backlog and
            (self.n_items_added - self.n_items_received == self.hq.max_backlog)
        )

    def history_is_full(self):
        return self.has_hq() and self.hq.history_full()

    @precondition(complement(has_hq))
    @rule(
        history_size=st.one_of(st.just(None), st.integers(min_value=0, max_value=4)),
        max_backlog=st.integers(min_value=0, max_value=4),
    )
    def initialize(self, history_size, max_backlog):
        self.hq = HistoryQueue(history_size, max_backlog=max_backlog)

    @preconditions(has_hq, complement(backlog_is_too_full))
    @rule(item=anything())
    def put(self, item):
        self.hq.put_nowait(item)
        self.items_added.append(item)

    @precondition(backlog_is_too_full)
    @rule(item=anything())
    def attempt_to_put(self, item):
        assert self.hq.backlog_full()
        with pytest.raises(asyncio.QueueFull):
            self.hq.put_nowait(item)

    @preconditions(has_hq, backlog_is_empty)
    def attempt_to_get(self):
        assert self.hq.backlog_empty()
        with pytest.raises(asyncio.QueueEmpty):
            self.hq.get_nowait()

    @precondition(complement(backlog_is_empty))
    @rule(target=items_received)
    def get(self):
        item = ReceivedItem(self.n_items_received, self.hq.get_nowait())
        print(item)
        self.n_items_received += 1
        return item

    @precondition(history_is_full)
    def check_full(self):
        assert self.hq.history_full()

    @rule(item=items_received)
    def check_item(self, item):
        if self.hq.history_size is None or item[0] <= self.hq.history_size:
            self.check_item_not_filled_yet(item)
        else:
            self.check_item_filled(item)

    def check_item_filled(self, item_off_bundle):
        i, item = item_off_bundle
        assert len(item) == self.hq.history_size + 1
        for item_added, item_received in zip(self.items_added[i - self.hq.history_size:],
                                             reversed(item)):
            assert item_added is item_received

    def check_item_not_filled_yet(self, item_off_bundle):
        i, item = item_off_bundle
        assert len(item) == i + 1
        for item_added, item_received in zip(self.items_added, reversed(item)):
            assert item_added is item_received


TestHQ = HQRules.TestCase


# https://github.com/HypothesisWorks/hypothesis-python/issues/292
class CoroTest(TestCase):
    timeout = 5

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def execute_example(self, f):
        error = None

        def g():
            nonlocal error
            try:
                x = f()
                if x is not None:
                    yield from x
            except BaseException as e:
                error = e

        coro = asyncio.coroutine(g)
        future = asyncio.wait_for(coro(), timeout=self.timeout)
        self.loop.run_until_complete(future)
        if error is not None:
            raise error

    @given(st.streaming(anything()))
    async def test_get_put(self, things):
        hq = HistoryQueue(history_size=2)
        assert hq.backlog_empty()

        it = iter(things)
        thing = next(it)
        await hq.put(thing)
        result = await hq.get()
        assert result == (thing,)
        assert result[0] is thing

        thing2 = next(it)
        await hq.put(thing2)
        result = await hq.get()
        assert result == (thing2, thing)
        assert result[0] is thing2
        assert result[1] is thing

        thing3 = next(it)
        await hq.put(thing3)
        thing4 = next(it)
        await hq.put(thing4)
        assert hq.backlog_size() == 2

        result = await hq.get()
        assert result == (thing3, thing2, thing)
        assert result[0] is thing3
        assert result[1] is thing2
        assert hq.history_full()

        thing5 = next(it)
        await hq.put(thing5)
        result = await hq.get()
        assert result == (thing4, thing3, thing2)
        assert result[0] is thing4

        hq.clear_history()
        thing6 = next(it)
        await hq.put(thing6)
        result = await hq.get()
        assert result == (thing5, thing4, thing3)
        assert result[0] is thing5

        result = await hq.get()
        assert result == (thing6,)
