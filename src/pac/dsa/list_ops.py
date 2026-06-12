class ListOps:
    _list = []

    @classmethod
    def call(cls, op, *args):
        if op == "new":
            cls._list = []
            return cls._list
        elif op == "append":
            cls._list.append(args[0])
            return cls._list
        elif op == "remove":
            cls._list.remove(args[0])
            return cls._list
        elif op == "get":
            return cls._list[args[0]]
        elif op == "size":
            return len(cls._list)
        elif op == "sort":
            cls._list.sort()
            return cls._list
        else:
            return f"Unknown list op: {op}"