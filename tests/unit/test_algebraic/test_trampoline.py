"""Tests for trampoline utilities."""

import asyncio
from collections.abc import Awaitable

import pytest

from effectful.algebraic.trampoline import (
    Continue,
    Done,
    TrampolineStep,
    async_trampoline,
    trampoline,
    unfold,
)


def factorial_step(n: int, acc: int = 1) -> TrampolineStep[int]:
    """Pure trampoline step for factorial."""
    if n <= 1:
        return Done(acc)

    def next_step() -> TrampolineStep[int]:
        return factorial_step(n - 1, n * acc)

    return Continue(next_step)


def identity_step(value: int) -> TrampolineStep[Awaitable[int]]:
    """Async trampoline step that awaits the final value."""

    async def _finish() -> int:
        return value

    return Done(_finish())


def test_trampoline_runs_to_completion() -> None:
    """trampoline should iterate Continue steps until Done is reached."""
    result = trampoline(factorial_step(5))
    assert result == 120


@pytest.mark.asyncio()
async def test_async_trampoline_runs_to_completion() -> None:
    """async_trampoline should await the final awaitable at Done."""
    result = await async_trampoline(identity_step(42))
    assert result == 42


@pytest.mark.asyncio()
async def test_async_trampoline_handles_continue_branch() -> None:
    """async_trampoline should follow Continue -> Done chain."""

    async def final_value() -> int:
        return 7

    def step() -> TrampolineStep[Awaitable[int]]:
        return Continue(lambda: Done(final_value()))

    result = await async_trampoline(step())
    assert result == 7


def test_unfold_builds_trampoline_steps() -> None:
    """unfold should wrap iterative logic into trampoline steps."""

    def decrement_until_zero(value: int) -> tuple[int, bool]:
        return (value, True) if value <= 0 else (value - 1, False)

    step = unfold(3, decrement_until_zero)
    assert isinstance(step, Continue)
    assert trampoline(step) == 0
