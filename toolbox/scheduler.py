import datetime
import asyncio
from typing import Callable

from toolbox.tools import Now

now = Now()


def get_delta(hour, minute, second):
    now_ = datetime.datetime.now()
    target_day = now_ + datetime.timedelta(1) if now_.hour > hour else now_
    target_time = datetime.datetime(target_day.year, target_day.month, target_day.day, hour, minute, second)
    return (target_time - now_).seconds + 1


class ScheduledTask:
    def __init__(self, target_time, task: Callable, args, once=False):
        self.target_time = target_time
        self._task = task
        self._args = args
        self._ok = True
        self._once = once
        self._worker = asyncio.ensure_future(self._schedule())
        print(f'[{now}] Task {self._task.__name__} has been scheduled at ' + '{:0>2}:{:0>2}:{:0>2}'.format(*self.target_time))

    async def _schedule(self):
        while self._ok:
            await asyncio.sleep(get_delta(*self.target_time))
            await asyncio.get_event_loop().run_in_executor(None, self._task, *self._args)
            if self._once:
                self._ok = False

    async def force_run(self):
        await asyncio.get_event_loop().run_in_executor(None, self._task, *self._args)

    def cancel(self):
        self._ok = False
        self._worker.cancel()
        print(f'[{now}] Task {self._task.__name__} has been canceled.')

    def __del__(self):
        if self._ok:
            self.cancel()


class PeriodicalTask:
    def __init__(self, frequency, task: Callable, args):
        self.frequency = frequency
        self._task = task
        self._args = args
        self._ok = True
        self._worker = asyncio.ensure_future(self._schedule())
        print(f'[{now}] Task {self._task.__name__} has been scheduled to run per {self.frequency} seconds.')

    async def _schedule(self):
        while self._ok:
            await asyncio.sleep(self.frequency)
            await asyncio.get_event_loop().run_in_executor(None, self._task, *self._args)

    async def force_run(self):
        await asyncio.get_event_loop().run_in_executor(None, self._task, *self._args)

    def cancel(self):
        self._ok = False
        self._worker.cancel()
        print(f'[{now}] Task {self._task.__name__} has been canceled.')

    def __del__(self):
        if self._ok:
            self.cancel()
