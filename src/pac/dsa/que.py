from collections import deque

class QueueOps:
    _queue = deque()

    @classmethod
    def call(cls, op, *args):
        if op == "new":
            cls._queue.clear()
        elif op == "enqueue":
            cls._queue.append(args[0])
        elif op == "dequeue":
            if cls._queue:
                return cls._queue.popleft()
            return None
        elif op == "front":
            if cls._queue:
                return cls._queue[0]
            return None
        return None