"""
Minimal pytest compatibility shim.
Used when the pytest package is not installed (e.g. offline CI environments).
Provides: raises, mark (parametrize, skip), skip.

When pytest IS installed this module is never imported because
'import pytest' resolves to the real package first.
"""

from __future__ import annotations

import contextlib
import inspect
import sys
import traceback
import unittest
from typing import Any, Callable, Generator, Type


# ---------------------------------------------------------------------------
# pytest.raises
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def raises(
    exc_type: Type[BaseException],
    *,
    match: str | None = None,
) -> Generator[Any, None, None]:
    import re as _re

    class _ExcInfo:
        value: BaseException | None = None

    info = _ExcInfo()
    try:
        yield info
    except exc_type as exc:
        info.value = exc
        if match is not None:
            if not _re.search(match, str(exc)):
                raise AssertionError(
                    f"Pattern {match!r} not found in exception message: {exc!r}"
                ) from exc
        return
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"Expected {exc_type.__name__} but got {type(exc).__name__}: {exc}"
        ) from exc

    raise AssertionError(f"Expected {exc_type.__name__} but no exception was raised")


# ---------------------------------------------------------------------------
# pytest.skip
# ---------------------------------------------------------------------------

class _SkipTest(Exception):
    """Mirrors unittest.SkipTest so our skip works with both runners."""


skip = unittest.SkipTest  # reuse unittest's exception


def _skip_function(reason: str) -> None:
    raise unittest.SkipTest(reason)


# ---------------------------------------------------------------------------
# pytest.mark
# ---------------------------------------------------------------------------

class _MarkDecorator:
    def __init__(self, name: str) -> None:
        self._name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # Returns a decorator when called with mark parameters
        def decorator(fn: Callable) -> Callable:
            if self._name == "parametrize":
                return _apply_parametrize(fn, *args, **kwargs)
            # Other marks (e.g. skip) just return fn unchanged for simplicity
            return fn
        # If called with a single callable (i.e. used as @mark.something)
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator

    def __getattr__(self, sub_name: str) -> "_MarkDecorator":
        return _MarkDecorator(sub_name)


def _apply_parametrize(fn: Callable, argnames: str, argvalues: list) -> Callable:  # type: ignore[type-arg]
    """
    Expand a parametrize mark into individual test methods on the class
    or as a plain list marker on standalone functions.
    This simple shim adds '_parametrize_cases' attribute for the runner.
    """
    fn._parametrize_names = [n.strip() for n in argnames.split(",")]
    fn._parametrize_cases = argvalues
    return fn


class _Mark:
    def __getattr__(self, name: str) -> _MarkDecorator:
        return _MarkDecorator(name)


mark = _Mark()


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def _run_test_function(fn: Callable, instance: Any = None) -> tuple[int, int, int]:
    """Run a single test function (possibly parametrized). Returns (passed, failed, skipped)."""
    passed = failed = skipped = 0

    cases: list[tuple] = []
    if hasattr(fn, "_parametrize_cases"):
        names = fn._parametrize_names
        for values in fn._parametrize_cases:
            if not isinstance(values, tuple):
                values = (values,)
            cases.append(dict(zip(names, values)))
    else:
        cases = [{}]

    for kwargs in cases:
        label = f"{fn.__name__}({', '.join(f'{k}={v!r}' for k, v in kwargs.items())})" if kwargs else fn.__name__
        try:
            if instance is not None:
                fn(instance, **kwargs)
            else:
                fn(**kwargs)
            print(f"    PASS  {label}")
            passed += 1
        except unittest.SkipTest as e:
            print(f"    SKIP  {label} ({e})")
            skipped += 1
        except AssertionError as e:
            print(f"    FAIL  {label}")
            traceback.print_exc()
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"    ERROR {label}")
            traceback.print_exc()
            failed += 1

    return passed, failed, skipped


def _run_module(module_path: str) -> tuple[int, int, int]:
    """Import and run all test classes/functions in a module file."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_test_mod", module_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    total_p = total_f = total_s = 0

    for name in dir(mod):
        obj = getattr(mod, name)
        if inspect.isclass(obj) and name.startswith("Test"):
            print(f"\n  {name}")
            instance = obj()
            for mname in dir(obj):
                mobj = getattr(obj, mname)
                if callable(mobj) and mname.startswith("test"):
                    p, f, s = _run_test_function(mobj, instance)
                    total_p += p; total_f += f; total_s += s
        elif callable(obj) and name.startswith("test_"):
            p, f, s = _run_test_function(obj)
            total_p += p; total_f += f; total_s += s

    return total_p, total_f, total_s


def main() -> None:
    """Discover and run all test_*.py files under tests/."""
    from pathlib import Path

    test_dir = Path(__file__).parent / "tests"
    files = sorted(test_dir.glob("test_*.py"))
    if not files:
        print("No test files found.")
        return

    grand_p = grand_f = grand_s = 0
    for f in files:
        print(f"\n{'='*60}\n{f.name}")
        p, fail, s = _run_module(str(f))
        grand_p += p; grand_f += fail; grand_s += s

    print(f"\n{'='*60}")
    print(f"Results: {grand_p} passed, {grand_f} failed, {grand_s} skipped")
    sys.exit(1 if grand_f else 0)
