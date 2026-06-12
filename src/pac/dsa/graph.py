class GraphOps:
    _adj = {}

    @classmethod
    def call(cls, op, *args):
        if op == "new":
            cls._adj.clear()
        elif op == "add_edge":
            u, v = args[0], args[1]
            cls._adj.setdefault(u, []).append(v)
            cls._adj.setdefault(v, []).append(u)
        elif op == "bfs":
            start = args[0]
            visited = set()
            queue = [start]
            order = []
            while queue:
                node = queue.pop(0)
                if node not in visited:
                    visited.add(node)
                    order.append(node)
                    queue.extend(cls._adj.get(node, []))
            return order
        elif op == "dfs":
            start = args[0]
            visited = set()
            order = []
            cls._dfs(start, visited, order)
            return order
        return None

    @classmethod
    def _dfs(cls, node, visited, order):
        if node not in visited:
            visited.add(node)
            order.append(node)
            for nei in cls._adj.get(node, []):
                cls._dfs(nei, visited, order)