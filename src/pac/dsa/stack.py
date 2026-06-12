class StackOps:
    _stack = []

    @classmethod
    def call(cls, op, *args):
        if op == "new":
            cls._stack = []
        elif op == "push":
            cls._stack.append(args[0])
        elif op == "pop":
            if cls._stack:
                return cls._stack.pop()
            return None
        elif op == "peek":
            if cls._stack:
                return cls._stack[-1]
            return None
        elif op == "is_empty":
            return len(cls._stack) == 0
        return None