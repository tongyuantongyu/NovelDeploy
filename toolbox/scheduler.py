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
        print(f'[{now}] Task {self._task.__name__} has been scheduled at ' +
              '{:0>2}:{:0>2}:{:0>2}.'.format(*self.target_time))

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


class AutoPostponeTask:
    def __init__(self, time_interval, task: Callable, args):
        self.busy_begin = time_interval[0]
        self.busy_end = time_interval[1]
        self.cross_date_change = self.busy_begin > self.busy_end
        self._task = task
        self._args = args
        print(f'[{now}] Task {self._task.__name__} has been created and will be postponed if between ' +
              '{:0>2}:{:0>2}:{:0>2} and {:0>2}:{:0>2}:{:0>2}.'.format(*self.busy_begin, *self.busy_end))

    async def _schedule(self):
        print(f'[{now}] Task {self._task.__name__} has been scheduled to run at ' +
              '{:0>2}:{:0>2}:{:0>2}.'.format(*self.busy_end))
        await asyncio.sleep(get_delta(*self.busy_end))
        await asyncio.get_event_loop().run_in_executor(None, self._task, *self._args)

    async def _run(self):
        await asyncio.get_event_loop().run_in_executor(None, self._task, *self._args)

    force_run = _run

    def run(self):
        now_ = datetime.datetime.now()
        now_tuple = (now_.hour, now_.minute, now_.second)
        if self.cross_date_change:
            if now_tuple < self.busy_end or now_tuple >= self.busy_begin:
                asyncio.ensure_future(self._schedule())
                return
        else:
            if self.busy_begin <= now_tuple < self.busy_end:
                asyncio.ensure_future(self._schedule())
                return
        asyncio.ensure_future(self._run())
