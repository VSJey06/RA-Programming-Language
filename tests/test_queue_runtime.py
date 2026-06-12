"""Runtime tests for Queue V1 operations.

Covers:
  - Queue creation (Queue.Q)
  - Push / Pop / Peek
  - Properties (size, count, empty)
  - Typed assignment from pop/peek
  - Error cases
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser
from runtime.runtime import Runtime, RuntimeError

PASS = 0
FAIL = 0


def ok(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        msg = f"  FAIL: {label}"
        if detail:
            msg += f"  ({detail})"
        print(msg)
        FAIL += 1


def run(code: str) -> Runtime:
    rt = Runtime()
    rt.execute(Parser(tokenize(code)).parse())
    return rt


# ── Creation ────────────────────────────────────────────────────────

def test_queue_create() -> None:
    rt = run("Queue.Q\n")
    ok("Queue.Q creates Q", rt.queue_engine.has("Q"))


def test_queue_create_multiple() -> None:
    rt = run("Queue.A\nQueue.B\n")
    ok("Queue.A and Queue.B exist",
       rt.queue_engine.has("A") and rt.queue_engine.has("B"))


# ── Push / Pop / Peek ──────────────────────────────────────────────

def test_push_and_pop() -> None:
    rt = run("Queue.Q\nQ.push:10\nQ.push:20\nQ.pop\n")
    ok("pop returns 10", rt.global_scope.get("_") == 10)


def test_push_and_pop_twice() -> None:
    rt = run("Queue.Q\nQ.push:10\nQ.push:20\nQ.pop\nQ.pop\n")
    ok("second pop returns 20", rt.global_scope.get("_") == 20)


def test_push_and_peek() -> None:
    rt = run("Queue.Q\nQ.push:10\nQ.push:20\nQ.peek\n")
    ok("peek returns 10 without removal", rt.global_scope.get("_") == 10)


def test_peek_preserves_queue() -> None:
    rt = run("Queue.Q\nQ.push:10\nQ.peek\nQ.pop\n")
    ok("pop after peek still returns 10", rt.global_scope.get("_") == 10)


def test_push_auto_creates() -> None:
    rt = run("AutoQ.push:5\nAutoQ.pop\n")
    ok("push auto-creates queue, pop returns 5", rt.global_scope.get("_") == 5)


def test_pop_string_value() -> None:
    rt = run('Queue.Q\nQ.push:"Ken"\nQ.pop\n')
    ok("pop returns 'Ken'", rt.global_scope.get("_") == "Ken")


# ── Properties ─────────────────────────────────────────────────────

def test_queue_size() -> None:
    rt = run("Queue.Q\nQ.push:1\nQ.push:2\nQ.size\n")
    ok("size = 2", rt.global_scope.get("_") == 2)


def test_queue_count() -> None:
    rt = run("Queue.Q\nQ.push:1\nQ.push:2\nQ.pop\nQ.count\n")
    ok("count = 1 after one pop", rt.global_scope.get("_") == 1)


def test_queue_empty_after_create() -> None:
    rt = run("Queue.Q\nQ.empty\n")
    ok("new queue is empty", rt.global_scope.get("_") is True)


def test_queue_not_empty_after_push() -> None:
    rt = run("Queue.Q\nQ.push:1\nQ.empty\n")
    ok("queue with element is not empty", rt.global_scope.get("_") is False)


def test_queue_empty_after_drain() -> None:
    rt = run("Queue.Q\nQ.push:1\nQ.pop\nQ.empty\n")
    ok("queue empty after draining", rt.global_scope.get("_") is True)


# ── Typed assignment ───────────────────────────────────────────────

def test_pop_to_var() -> None:
    rt = run("Queue.Q\nQ.push:42\nI x = Q.pop\n")
    ok("x = 42 via pop", rt.global_scope.get("x") == 42)


def test_peek_to_var() -> None:
    rt = run("Queue.Q\nQ.push:7\nQ.push:8\nI y = Q.peek\n")
    ok("y = 7 via peek", rt.global_scope.get("y") == 7)


# ── Error cases ────────────────────────────────────────────────────

def test_pop_empty_raises() -> None:
    try:
        run("Queue.Q\nQ.pop\n")
        ok("pop empty raises", False)
    except RuntimeError:
        ok("pop empty raises", True)


def test_peek_empty_raises() -> None:
    try:
        run("Queue.Q\nQ.peek\n")
        ok("peek empty raises", False)
    except RuntimeError:
        ok("peek empty raises", True)


# ── Run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_queue_create()
    test_queue_create_multiple()
    test_push_and_pop()
    test_push_and_pop_twice()
    test_push_and_peek()
    test_peek_preserves_queue()
    test_push_auto_creates()
    test_pop_string_value()
    test_queue_size()
    test_queue_count()
    test_queue_empty_after_create()
    test_queue_not_empty_after_push()
    test_queue_empty_after_drain()
    test_pop_to_var()
    test_peek_to_var()
    test_pop_empty_raises()
    test_peek_empty_raises()

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  {PASS} passed, {FAIL} failed out of {total} tests")
    sys.exit(0 if FAIL == 0 else 1)
