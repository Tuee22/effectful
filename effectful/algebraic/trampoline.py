"""Trampoline pattern for stack-safe recursion.

Python doesn't optimize tail calls, so naive recursion causes stack overflows.
The trampoline pattern converts recursion to iteration while preserving functional semantics.

Example usage:
    from effectful.algebraic.trampoline import Continue, Done, TrampolineStep, trampoline

    def factorial_step(n: int, acc: int = 1) -> TrampolineStep[int]:
        return (
            Done(acc) if n <= 1
            else Continue(lambda n=n, acc=acc: factorial_step(n - 1, n * acc))
        )

    result = trampoline(factorial_step(10000))  # No stack overflow!
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Continue(Generic[T]):
    """Signal to continue with another computation step.

    The thunk is a zero-argument callable that returns the next TrampolineStep.
    Using a thunk (lazy evaluation) prevents building up the call stack.
    """

    thunk: Callable[[], "TrampolineStep[T]"]


@dataclass(frozen=True)
class Done(Generic[T]):
    """Signal that computation is complete with a final value."""

    value: T


type TrampolineStep[T] = Continue[T] | Done[T]


def trampoline(step: TrampolineStep[T]) -> T:
    """Execute trampoline steps until completion.

    This is the single controlled iteration point in the codebase.
    The while loop here is acceptable as it's the trampoline driver.

    Args:
        step: Initial TrampolineStep to execute

    Returns:
        The final value when Done is reached
    """
    current = step
    while True:  # Acceptable: controlled trampoline iteration point
        match current:
            case Done(value=value):
                return value
            case Continue(thunk=thunk):
                current = thunk()


async def async_trampoline(step: TrampolineStep[Awaitable[T]]) -> T:
    """Async version of trampoline for effect interpretation.

    Each step returns an Awaitable that is awaited when Done is reached.

    Args:
        step: Initial TrampolineStep containing Awaitables

    Returns:
        The awaited final value
    """
    current = step
    while True:  # Acceptable: controlled trampoline iteration point
        match current:
            case Done(value=awaitable):
                return await awaitable
            case Continue(thunk=thunk):
                current = thunk()


def unfold(
    seed: T,
    step_fn: Callable[[T], tuple[T, bool]],
) -> TrampolineStep[T]:
    """Create a trampoline from an unfold pattern.

    Useful for converting imperative loops to trampolines.

    Args:
        seed: Initial value
        step_fn: Function returning (next_value, is_done)

    Returns:
        TrampolineStep that unfolds the computation
    """
    next_val, is_done = step_fn(seed)
    return Done(next_val) if is_done else Continue(lambda: unfold(next_val, step_fn))


__all__ = [
    "Continue",
    "Done",
    "TrampolineStep",
    "trampoline",
    "async_trampoline",
    "unfold",
]
