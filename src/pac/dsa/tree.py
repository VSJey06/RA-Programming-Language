class Node:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

class TreeOps:
    _root = None

    @classmethod
    def call(cls, op, *args):
        if op == "new":
            cls._root = None
        elif op == "insert":
            cls._root = cls._insert(cls._root, args[0])
        elif op == "search":
            return cls._search(cls._root, args[0])
        elif op == "inorder":
            result = []
            cls._inorder(cls._root, result)
            return result
        return None

    @staticmethod
    def _insert(root, val):
        if root is None:
            return Node(val)
        if val < root.val:
            root.left = TreeOps._insert(root.left, val)
        else:
            root.right = TreeOps._insert(root.right, val)
        return root

    @staticmethod
    def _search(root, val):
        if root is None or root.val == val:
            return root is not None
        if val < root.val:
            return TreeOps._search(root.left, val)
        return TreeOps._search(root.right, val)

    @staticmethod
    def _inorder(root, out):
        if root:
            TreeOps._inorder(root.left, out)
            out.append(root.val)
            TreeOps._inorder(root.right, out)