"""Tests for Result[T, E] type.

This module provides comprehensive tests for the Result type including:
- Ok and Err construction
- Immutability (frozen dataclass)
- Type predicates (is_ok, is_err)
- Functor operations (map, map_err)
- Monad operations (flat_map)
- Value extraction (unwrap, unwrap_or, unwrap_err)
- Fold pattern for exhaustive matching
"""

from dataclasses import FrozenInstanceError

import pytest

from functional_effects.algebraic.result import Err, Ok, Result, fold_result


class TestOkConstruction:
    """Test Ok variant construction and immutability."""

    def test_ok_creates_success_result(self) -> None:
        """Ok should wrap a value."""
        result: Result[int, str] = Ok(42)
        assert isinstance(result, Ok)
        assert result.value == 42

    def test_ok_is_immutable(self) -> None:
        """Ok should be frozen (immutable)."""
        result = Ok(42)
        with pytest.raises(FrozenInstanceError):
            result.value = 100  # type: ignore[misc]


class TestOkPredicates:
    """Test Ok type predicates."""

    def test_ok_is_ok_returns_true(self) -> None:
        """Ok.is_ok() should return True."""
        result: Result[int, str] = Ok(42)
        assert result.is_ok() is True

    def test_ok_is_err_returns_false(self) -> None:
        """Ok.is_err() should return False."""
        result: Result[int, str] = Ok(42)
        assert result.is_err() is False


class TestOkFunctor:
    """Test Ok functor operations (map)."""

    def test_ok_map_applies_function(self) -> None:
        """Ok.map() should apply function to wrapped value."""
        result = Ok[int](42)
        mapped = result.map(lambda x: x * 2)
        assert mapped.unwrap() == 84

    def test_ok_map_preserves_ok(self) -> None:
        """Ok.map() should preserve Ok variant."""
        result = Ok[int](42)
        mapped = result.map(lambda x: str(x))
        assert mapped.is_ok()

    def test_ok_map_err_is_noop(self) -> None:
        """Ok.map_err() should be a no-op for Ok."""
        result = Ok[int](42)
        mapped = result.map_err(lambda e: str(e).upper())
        assert mapped.unwrap() == 42


class TestOkMonad:
    """Test Ok monad operations (flat_map)."""

    def test_ok_flat_map_chains_ok(self) -> None:
        """Ok.flat_map() should chain another Ok computation."""
        result = Ok[int](42)
        chained: Result[int, str] = result.flat_map(lambda x: Ok(x * 2))
        assert chained.unwrap() == 84

    def test_ok_flat_map_chains_err(self) -> None:
        """Ok.flat_map() can chain to Err."""
        result = Ok[int](42)
        chained: Result[int, str] = result.flat_map(lambda _: Err("error"))
        assert chained.is_err()
        assert chained.unwrap_err() == "error"


class TestOkUnwrap:
    """Test Ok value extraction."""

    def test_ok_unwrap_returns_value(self) -> None:
        """Ok.unwrap() should return the wrapped value."""
        result: Result[int, str] = Ok(42)
        assert result.unwrap() == 42

    def test_ok_unwrap_or_returns_value(self) -> None:
        """Ok.unwrap_or() should return the value, not the default."""
        result: Result[int, str] = Ok(42)
        assert result.unwrap_or(0) == 42

    def test_ok_unwrap_err_raises(self) -> None:
        """Ok.unwrap_err() should raise ValueError."""
        result: Result[int, str] = Ok(42)
        with pytest.raises(ValueError, match="Called unwrap_err on Ok"):
            result.unwrap_err()


class TestErrConstruction:
    """Test Err variant construction and immutability."""

    def test_err_creates_failure_result(self) -> None:
        """Err should wrap an error."""
        result: Result[int, str] = Err("error")
        assert isinstance(result, Err)

        assert result.error == "error"

    def test_err_is_immutable(self) -> None:
        """Err should be frozen (immutable)."""
        result = Err("error")
        with pytest.raises(FrozenInstanceError):
            result.error = "new error"  # type: ignore[misc]


class TestErrPredicates:
    """Test Err type predicates."""

    def test_err_is_ok_returns_false(self) -> None:
        """Err.is_ok() should return False."""
        result: Result[int, str] = Err("error")
        assert result.is_ok() is False

    def test_err_is_err_returns_true(self) -> None:
        """Err.is_err() should return True."""
        result: Result[int, str] = Err("error")
        assert result.is_err() is True


class TestErrFunctor:
    """Test Err functor operations (map, map_err)."""

    def test_err_map_is_noop(self) -> None:
        """Err.map() should be a no-op for Err."""
        result = Err[str]("error")
        mapped = result.map(lambda x: str(x))  # Lambda never called on Err
        assert mapped.is_err()
        assert mapped.unwrap_err() == "error"

    def test_err_map_err_applies_function(self) -> None:
        """Err.map_err() should apply function to error."""
        result = Err[str]("error")
        mapped = result.map_err(lambda e: e.upper())
        assert mapped.unwrap_err() == "ERROR"


class TestErrMonad:
    """Test Err monad operations (flat_map)."""

    def test_err_flat_map_is_noop(self) -> None:
        """Err.flat_map() should be a no-op for Err."""
        result = Err[str]("error")
        chained = result.flat_map(lambda x: Ok(str(x)))  # Lambda never called on Err
        assert chained.is_err()
        assert chained.unwrap_err() == "error"


class TestErrUnwrap:
    """Test Err value extraction."""

    def test_err_unwrap_raises(self) -> None:
        """Err.unwrap() should raise ValueError."""
        result: Result[int, str] = Err("error")
        with pytest.raises(ValueError, match="Called unwrap on Err"):
            result.unwrap()

    def test_err_unwrap_or_returns_default(self) -> None:
        """Err.unwrap_or() should return the default."""
        result: Result[int, str] = Err("error")
        assert result.unwrap_or(0) == 0

    def test_err_unwrap_err_returns_error(self) -> None:
        """Err.unwrap_err() should return the error."""
        result: Result[int, str] = Err("error")
        assert result.unwrap_err() == "error"


class TestFoldResult:
    """Test fold_result for exhaustive matching."""

    def test_fold_result_handles_ok(self) -> None:
        """fold_result should apply on_ok for Ok."""
        result: Result[int, str] = Ok(42)
        value = fold_result(
            result,
            on_ok=lambda x: x * 2,
            on_err=lambda _: 0,
        )
        assert value == 84

    def test_fold_result_handles_err(self) -> None:
        """fold_result should apply on_err for Err."""
        result: Result[int, str] = Err("error")
        value = fold_result(
            result,
            on_ok=lambda x: x * 2,
            on_err=lambda _: 0,
        )
        assert value == 0

    def test_fold_result_is_exhaustive(self) -> None:
        """fold_result should handle all Result variants."""
        # Type checker ensures this at compile time
        # If we add a new variant, this would fail to type check
        results: list[Result[int, str]] = [Ok(42), Err("error")]
        values = [
            fold_result(
                r,
                on_ok=lambda x: f"ok:{x}",
                on_err=lambda e: f"err:{e}",
            )
            for r in results
        ]
        assert values == ["ok:42", "err:error"]
