from collections import deque
import asyncio

__version__ = '0.2.0'


class HistoryQueue:
    def __init__(self, history_size=None, max_backlog=0, loop=None):
        """``asyncio.Queue`` with history.

        Objects put on a ``HistoryQueue`` are gathered in tuples,
        with the first element being the next item on the queue,
        followed by items add previously.

        ``HistoryQueue`` can also be thought of as as asynchronous ``collections.deque``,
        with ``put`` analogous to ``deque.appendleft``
        and ``get`` returning the entire deque (as a tuple).

        Up to ``history_size + 1`` items are returned in each tuple.
        If `history_size` is ``None``, then each tuple will contain the entire history of the queue.

        If `max_backlog` is less than or equal to zero, the queue size is infinite.
        If it is an integer greater than ``0``,
        then ``await put()``will block when the queue contains `max_backlog` items,
        until an item is removed by ``get``.

        If the queue is empty, ``await get()`` will block until an item is added to the queue.

        Parameters
        ----------
        history_size : int, optional
            The number of items, in addition to the "current" item, to return from ``get``.
            When `history_size` is ``None``, then entire history is returned.
            Serves a similar purpose as ``collections.deque.maxlen``.
        max_backlog : int, optional
            The number of items to save before the queue is considered full.
            If `max_backlog` is ``0``, the queue is never full.
            Analogous to ``asyncio.Queue.maxsize``.
        loop : ``asyncio.BaseEventLoop``, optional
            The event loop that will be managing the queue.

        Attributes
        ----------
        history_size
        max_backlog

        Raises
        ------
        ``QueueEmpty``
            When ``get_nowait`` is called on an empty queue.
        ``QueueFull``
            When ``put_nowait`` is called on a full queue.

        See Also
        --------
        ``asyncio.Queue``
        ``collections.deque``

        Notes
        -----
        This class is ``not thread safe``.

        Examples
        --------
        For ease of illustration, in these examples we use ``put_nowait`` and ``get_nowait``,
        the synchronous counterparts of ``put`` and ``wait``, respectively.
        In a coroutine, ``await put()`` could be used to block until the queue is not full,
        and ``await get()`` to block until there is an item in the queue.

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

        """
        self.history_size = history_size
        self.max_backlog = max_backlog

        self._deque = deque(maxlen=history_size if history_size is None else history_size + 1)
        self._queue = asyncio.Queue(maxsize=max_backlog, loop=loop)

    def backlog_empty(self):
        """Return ``True`` if the queue is empty ,``False`` otherwise.

        Returns
        -------
        bool

        """
        return self._queue.empty()

    def backlog_full(self):
        """
        Return ``True`` if there are `max_backlog` items in the queue.

        Returns
        -------
        bool

        """
        return self._queue.full()

    def history_full(self):
        """Return ``True`` if at least ``history_size + 1`` items have been put on the queue.

        Returns
        -------
        bool

        """
        return len(self._deque) == self._deque.maxlen

    async def get(self):
        """Return the current item on the queue, with history (if any).
        If queue is empty, wait until an item is available.

        Returns
        -------
        tuple

        """
        return await self._queue.get()

    def get_nowait(self):
        """Return the current item on the queue, with history (if any).
         If no item is immediately available, raise |QueueEmpty|.

        Returns
        -------
        tuple

        """
        return self._queue.get_nowait()

    async def put(self, item):
        """Put an item into the queue.
        If the queue is full, wait until a free slot is available.

        Parameters
        ----------
        item

        """
        self._deque.appendleft(item)
        await self._queue.put(self._as_tuple())

    def put_nowait(self, item):
        """Put an item into the queue.
        If no slot is immediately available, raise |QueueFull|.

        Parameters
        ----------
        item

        """
        initial_deque = self._deque.copy()
        self._deque.appendleft(item)
        try:
            self._queue.put_nowait(self._as_tuple())
        except asyncio.QueueFull:
            # If the QueueFull exception is caught, pretend nothing happened.
            self._deque = initial_deque
            raise

    def backlog_size(self):
        """Number of items in the queue.

        Returns
        -------
        int

        """
        return self._queue.qsize()

    def clear_history(self):
        """"Clears the history.
        All items already put on the queue will remain,
        but the next item put on the queue will have no history associated with it
        when it is eventually returned.

        """
        self._deque = deque(maxlen=self.history_size + 1)

    def _as_tuple(self):
        return tuple(self._deque)

    def __repr__(self):
        return '<{} at {} history_size={}, max_backlog={}>'.format(
            type(self).__name__, hex(id(self)), self.history_size, self.max_backlog,
        )
