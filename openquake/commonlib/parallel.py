# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2010-2014, GEM Foundation.
#
# OpenQuake is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake.  If not, see <http://www.gnu.org/licenses/>.

"""
TODO: write documentation.
"""

import os
import sys
import logging
import operator
import traceback
from concurrent.futures import as_completed, ProcessPoolExecutor
from decorator import FunctionMaker
import psutil

from openquake.baselib.python3compat import pickle
from openquake.baselib.performance import PerformanceMonitor, DummyMonitor
from openquake.baselib.general import split_in_blocks, AccumDict, humansize


if psutil.__version__ > '2.0.0':  # Ubuntu 14.10
    def virtual_memory():
        return psutil.virtual_memory()

    def memory_info(proc):
        return proc.memory_info()

elif psutil.__version__ >= '1.2.1':  # Ubuntu 14.04
    def virtual_memory():
        return psutil.virtual_memory()

    def memory_info(proc):
        return proc.get_memory_info()

else:  # Ubuntu 12.04
    def virtual_memory():
        return psutil.phymem_usage()

    def memory_info(proc):
        return proc.get_memory_info()


executor = ProcessPoolExecutor()
# the num_tasks_hint is chosen to be 8 times bigger than the name of
# cores; it is a heuristic number to get a distribution of the
# load good for our cluster; it has no more significance than that
executor.num_tasks_hint = executor._max_workers * 8


def no_distribute():
    """
    True if the variable OQ_NO_DISTRIBUTE is true
    """
    nd = os.environ.get('OQ_NO_DISTRIBUTE', '').lower()
    return nd in ('1', 'true', 'yes')


def check_mem_usage(soft_percent=90, hard_percent=100):
    """
    Display a warning if we are running out of memory

    :param int mem_percent: the memory limit as a percentage
    """
    used_mem_percent = virtual_memory().percent
    if used_mem_percent > soft_percent:
        logging.warn('Using over %d%% of the memory!', used_mem_percent)
    if used_mem_percent > hard_percent:
        raise MemoryError('Using more memory than allowed by configuration '
                          '(Used: %d%% / Allowed: %d%%)! Shutting down.' %
                          (used_mem_percent, hard_percent))


def safely_call(func, args, pickle=False):
    """
    Call the given function with the given arguments safely, i.e.
    by trapping the exceptions. Return a pair (result, exc_type)
    where exc_type is None if no exceptions occur, otherwise it
    is the exception class and the result is a string containing
    error message and traceback.

    :param func: the function to call
    :param args: the arguments
    :param pickle:
        if set, the input arguments are unpickled and the return value
        is pickled; otherwise they are left unchanged
    """
    if pickle:
        args = [a.unpickle() for a in args]
    ismon = args and isinstance(args[-1], PerformanceMonitor)
    mon = args[-1] if ismon else DummyMonitor()
    try:
        res = func(*args), None, mon
    except:
        etype, exc, tb = sys.exc_info()
        tb_str = ''.join(traceback.format_tb(tb))
        res = ('\n%s%s: %s' % (tb_str, etype.__name__, exc), etype, mon)
    if pickle:
        return Pickled(res)
    return res


def log_percent_gen(taskname, todo, progress):
    """
    Generator factory. Each time the generator object is called
    log a message if the percentage is bigger than the last one.
    Yield the number of calls done at the current iteration.

    :param str taskname:
        the name of the task
    :param int todo:
        the number of times the generator object will be called
    :param progress:
        a logging function for the progress report
    """
    yield 0
    done = 1
    prev_percent = 0
    while done < todo:
        percent = int(float(done) / todo * 100)
        if percent > prev_percent:
            progress('%s %3d%%', taskname, percent)
            prev_percent = percent
        yield done
        done += 1
    progress('%s 100%%', taskname)
    yield done


class Pickled(object):
    """
    An utility to manually pickling/unpickling objects.
    The reason is that celery does not use the HIGHEST_PROTOCOL,
    so relying on celery is slower. Moreover Pickled instances
    have a nice string representation and length giving the size
    of the pickled bytestring.

    :param obj: the object to pickle
    """
    def __init__(self, obj):
        self.clsname = obj.__class__.__name__
        self.pik = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)

    def __repr__(self):
        """String representation of the pickled object"""
        return '<Pickled %s %s>' % (self.clsname, humansize(len(self)))

    def __len__(self):
        """Length of the pickled bytestring"""
        return len(self.pik)

    def unpickle(self):
        """Unpickle the underlying object"""
        return pickle.loads(self.pik)


def get_pickled_sizes(obj):
    """
    Return the pickled sizes of an object and its direct attributes,
    ordered by decreasing size. Here is an example:

    >> total_size, partial_sizes = get_pickled_sizes(PerformanceMonitor(''))
    >> total_size
    345
    >> partial_sizes
    [('_procs', 214), ('exc', 4), ('mem', 4), ('start_time', 4),
    ('_start_time', 4), ('duration', 4)]

    Notice that the sizes depend on the operating system and the machine.
    """
    sizes = []
    attrs = getattr(obj, '__dict__',  {})
    for name, value in attrs.items():
        sizes.append((name, len(Pickled(value))))
    return len(Pickled(obj)), sorted(
        sizes, key=lambda pair: pair[1], reverse=True)


def pickle_sequence(objects):
    """
    Convert an iterable of objects into a list of pickled objects.
    If the iterable contains copies, the pickling will be done only once.
    If the iterable contains objects already pickled, they will not be
    pickled again.

    :param objects: a sequence of objects to pickle
    """
    cache = {}
    out = []
    for obj in objects:
        obj_id = id(obj)
        if obj_id not in cache:
            if isinstance(obj, Pickled):  # already pickled
                cache[obj_id] = obj
            else:  # pickle the object
                cache[obj_id] = Pickled(obj)
        out.append(cache[obj_id])
    return out


class TaskManager(object):
    """
    A manager to submit several tasks of the same type.
    The usage is::

      tm = TaskManager(do_something, logging.info)
      tm.send(arg1, arg2)
      tm.send(arg3, arg4)
      print tm.reduce()

    Progress report is built-in.
    """
    executor = executor
    progress = staticmethod(logging.info)

    @classmethod
    def restart(cls):
        cls.executor.shutdown()
        cls.executor = ProcessPoolExecutor()

    @classmethod
    def starmap(cls, task, task_args, name=None):
        """
        Spawn a bunch of tasks with the given list of arguments

        :returns: a TaskManager object with a .result method.
        """
        self = cls(task, name)
        for i, a in enumerate(task_args, 1):
            cls.progress('Submitting task %s #%d', self.name, i)
            self.submit(*a)
        return self

    @classmethod
    def apply_reduce(cls, task, task_args, agg=operator.add, acc=None,
                     concurrent_tasks=executor._max_workers,
                     weight=lambda item: 1,
                     key=lambda item: 'Unspecified',
                     name=None):
        """
        Apply a task to a tuple of the form (sequence, \*other_args)
        by first splitting the sequence in chunks, according to the weight
        of the elements and possibly to a key (see :function:
        `openquake.baselib.general.split_in_blocks`).
        Then reduce the results with an aggregation function.
        The chunks which are generated internally can be seen directly (
        useful for debugging purposes) by looking at the attribute `._chunks`,
        right after the `apply_reduce` function has been called.

        :param task: a task to run in parallel
        :param task_args: the arguments to be passed to the task function
        :param agg: the aggregation function
        :param acc: initial value of the accumulator (default empty AccumDict)
        :param concurrent_tasks: hint about how many tasks to generate
        :param weight: function to extract the weight of an item in arg0
        :param key: function to extract the kind of an item in arg0
        """
        arg0 = task_args[0]  # this is assumed to be a sequence
        num_items = len(arg0)
        args = task_args[1:]
        task_func = getattr(task, 'task_func', task)
        if acc is None:
            acc = AccumDict()
        if num_items == 0:  # nothing to do
            return acc
        elif num_items == 1:  # apply the function in the master process
            return agg(acc, task_func(arg0, *args))
        chunks = list(split_in_blocks(
            arg0, concurrent_tasks or 1, weight, key))
        cls.apply_reduce.__func__._chunks = chunks
        if not concurrent_tasks or no_distribute():
            for chunk in chunks:
                acc = agg(acc, task_func(chunk, *args))
            return acc
        logging.info('Starting %d tasks', len(chunks))
        self = cls.starmap(task, [(chunk,) + args for chunk in chunks], name)
        return self.reduce(agg, acc)

    def __init__(self, oqtask, name=None):
        self.oqtask = oqtask
        self.task_func = getattr(oqtask, 'task_func', oqtask)
        self.name = name or oqtask.__name__
        self.results = []
        self.sent = 0
        self.received = 0
        self.no_distribute = no_distribute()

    def submit(self, *args):
        """
        Submit a function with the given arguments to the process pool
        and add a Future to the list `.results`. If the variable
        OQ_NO_DISTRIBUTE is set, the function is run in process and the
        result is returned.
        """
        check_mem_usage()
        # log a warning if too much memory is used
        if self.no_distribute:
            res = safely_call(self.task_func, args)
        else:
            piks = pickle_sequence(args)
            self.sent += sum(len(p) for p in piks)
            res = self._submit(piks)
        self.results.append(res)

    def _submit(self, piks):
        # submit tasks by using the ProcessPoolExecutor
        if self.oqtask is self.task_func:
            return self.executor.submit(
                safely_call, self.task_func, piks, True)
        else:  # call the decorated task
            return self.executor.submit(self.oqtask, *piks)

    def aggregate_result_set(self, agg, acc):
        """
        Loop on a set of futures and update the accumulator
        by using the aggregation function.

        :param agg: the aggregation function, (acc, val) -> new acc
        :param acc: the initial value of the accumulator
        :returns: the final value of the accumulator
        """
        for future in as_completed(self.results):
            check_mem_usage()
            # log a warning if too much memory is used
            result = future.result()
            if isinstance(result, BaseException):
                raise result
            self.received += len(result)
            acc = agg(acc, result.unpickle())
        return acc

    def reduce(self, agg=operator.add, acc=None):
        """
        Loop on a set of results and update the accumulator
        by using the aggregation function.

        :param agg: the aggregation function, (acc, val) -> new acc
        :param acc: the initial value of the accumulator
        :returns: the final value of the accumulator
        """
        if acc is None:
            acc = AccumDict()
        log_percent = log_percent_gen(
            self.name, len(self.results), self.progress)
        next(log_percent)

        def agg_and_percent(acc, triple):
            (val, exc, mon) = triple
            if exc:
                raise RuntimeError(val)
            res = agg(acc, val)
            next(log_percent)
            mon.flush()
            return res

        if self.no_distribute:
            agg_result = reduce(agg_and_percent, self.results, acc)
        else:
            self.progress('Sent %s of data', humansize(self.sent))
            agg_result = self.aggregate_result_set(agg_and_percent, acc)
            self.progress('Received %s of data', humansize(self.received))
        self.results = []
        return agg_result

    def wait(self):
        """
        Wait until all the task terminate. Discard the results.

        :returns: the total number of tasks that were spawned
        """
        return self.reduce(self, lambda acc, res: acc + 1, 0)

    def __iter__(self):
        """
        An iterator over the results
        """
        return iter(self.results)

# convenient aliases
starmap = TaskManager.starmap
apply_reduce = TaskManager.apply_reduce


def do_not_aggregate(acc, value):
    """
    Do nothing aggregation function, use it in
    :class:`openquake.commonlib.parallel.apply_reduce` calls
    when no aggregation is required.

    :param acc: the accumulator
    :param value: the value to accumulate
    :returns: the accumulator unchanged
    """
    return acc


class NoFlush(object):
    # this is instantiated by the litetask decorator
    def __init__(self, monitor, taskname):
        self.monitor = monitor
        self.taskname = taskname

    def __call__(self):
        raise RuntimeError('PerformanceMonitor(%r).flush() must not be called '
                           'by %s!' % (self.monitor.operation, self.taskname))


def rec_delattr(mon, name):
    """
    Delete attribute from a monitor recursively
    """
    for child in mon.children:
        rec_delattr(child, name)
    if name in vars(mon):
        delattr(mon, name)


def litetask(func):
    """
    Add monitoring support to the decorated function. The last argument
    must be a monitor object.
    """
    def wrapper(*args):
        monitor = args[-1]
        monitor.flush = NoFlush(monitor, func.__name__)
        with monitor('total ' + func.__name__, measuremem=True):
            result = func(*args)
        rec_delattr(monitor, 'flush')
        return result
    # NB: we need pickle=True because celery is using the worst possible
    # protocol; once we remove celery we can try to remove pickle=True
    return FunctionMaker.create(
        func, 'return _s_(_w_, (%(shortsignature)s,), pickle=True)',
        dict(_s_=safely_call, _w_=wrapper), task_func=func)
