"""Algebraic types for functional programming.

This package provides core algebraic types used throughout the functional effects system:
- Result[T, E]: Sum type for success/failure (Ok | Err)
- EffectReturn[T]: Wrapper for type-safe effect results
- Trampoline: Stack-safe recursion pattern (Continue | Done)
"""

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result, assert_never, fold_result, unreachable
from effectful.algebraic.trampoline import (
    Continue,
    Done,
    TrampolineStep,
    async_trampoline,
    trampoline,
    unfold,
)

__all__ = [
    "Result",
    "Ok",
    "Err",
    "fold_result",
    "assert_never",
    "unreachable",
    "EffectReturn",
    "Continue",
    "Done",
    "TrampolineStep",
    "trampoline",
    "async_trampoline",
    "unfold",
]
