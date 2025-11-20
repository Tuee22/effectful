"""Algebraic types for functional programming.

This package provides core algebraic types used throughout the functional effects system:
- Result[T, E]: Sum type for success/failure (Ok | Err)
- EffectReturn[T]: Wrapper for type-safe effect results
"""

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result, fold_result

__all__ = [
    "Result",
    "Ok",
    "Err",
    "fold_result",
    "EffectReturn",
]
