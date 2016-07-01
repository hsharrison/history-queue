========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - tests
      - | |travis|
        | |coveralls|
    * - package
      - |version| |downloads| |wheel| |supported-versions| |supported-implementations|

.. |travis| image:: https://travis-ci.org/hsharrison/history-queue.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/hsharrison/history-queue

.. |coveralls| image:: https://coveralls.io/repos/hsharrison/history-queue/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/hsharrison/history-queue

.. |version| image:: https://img.shields.io/pypi/v/hqueue.svg?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/hqueue

.. |downloads| image:: https://img.shields.io/pypi/dm/hqueue.svg?style=flat
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/hqueue

.. |wheel| image:: https://img.shields.io/pypi/wheel/hqueue.svg?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/hqueue

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/hqueue.svg?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/hqueue

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/hqueue.svg?style=flat
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/hqueue


.. end-badges

``asyncio.Queue`` with history::

Objects put on a ``HistoryQueue`` are gathered in tuples,
with the first element being the next item on the queue,
followed by items add previously.

``HistoryQueue`` can also be thought of as as asynchronous ``collections.deque``,
with ``put`` analogous to ``deque.appendleft``
and ``get`` returning the entire deque (as a tuple).

    >>> from hqueue import HistoryQueue
    >>> hq = HistoryQueue(history_size=2)
    >>> hq.put_nowait(0)
    >>> hq.put_nowait(1)
    >>> hq.get_nowait()
    (0,)
    >>> hq.get_nowait()
    (1, 0)
    >>> hq.put_nowait(2)
    >>> hq.put_nowait(3)
    >>> hq.put_nowait(4)
    >>> hq.get_nowait()
    (2, 1, 0)
    >>> hq.get_nowait()
    (3, 2, 1)

For ease of illustration, in the above examples we use ``put_nowait`` and ``get_nowait``,
the synchronous counterparts of ``put`` and ``wait``, respectively.
In a coroutine, ``await put()`` could be used to block until the queue is not full,
and ``await get()`` to block until there is an item in the queue.

See Also
--------
``asyncio.Queue``
``collections.deque``

