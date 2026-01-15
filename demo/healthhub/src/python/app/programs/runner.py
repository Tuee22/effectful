"""Program runner for effect execution.

Boundary: PROOF
Target-Language: Rust

Layer 2 in 5-layer architecture: Executes generator-based effect programs.
Returns typed Result values to avoid leaking interpreter exceptions.

Invariants:
- Never swallows exceptions (wraps in Err)
- Always returns typed Result
- Effect execution order matches program yield order
"""

from collections.abc import Generator
from dataclasses import dataclass
from typing import TypeVar

from effectful.algebraic.result import Err, Ok, Result

from app.domain.lookup_result import PatientFound, PatientMissingById, PatientMissingByUserId
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from typing import Protocol

T = TypeVar("T")


class InterpreterProtocol(Protocol):
    async def handle(self, effect: AllEffects) -> object:
        ...


@dataclass(frozen=True)
class InterpreterFailure:
    """Interpreter raised unexpectedly while executing an effect."""

    effect: AllEffects
    message: str


async def run_program(
    program: Generator[AllEffects, object, T], interpreter: InterpreterProtocol
) -> Result[T, InterpreterFailure]:
    """Execute an effect program to completion.

    This is the core effect execution loop (Layer 2):
    1. Program yields effect
    2. Runner sends effect to interpreter
    3. Interpreter returns result
    4. Runner sends result back to program
    5. Repeat until program completes

    Args:
        program: Generator that yields effects
        interpreter: Composite interpreter to handle effects

    Returns:
        Result[final program value, InterpreterFailure]

    Example:
        ```python
        def greet_patient(patient_id: UUID) -> Generator[AllEffects, object, str]:
            patient_result = yield GetPatientById(patient_id=patient_id)
            match patient_result:
                case PatientFound(patient=patient):
                    return f"Hello {patient.first_name}!"
                case PatientMissingById():
                    return "Patient not found"
                case PatientMissingByUserId():
                    return "Patient not found"

        result = unwrap_program_result(await run_program(greet_patient(patient_id), interpreter))
        ```
    """
    effect_result: object = None

    try:
        while True:
            # Step program: send previous result, receive next effect
            effect = program.send(effect_result)

            # Execute effect via interpreter
            try:
                effect_result = await interpreter.handle(effect)
            except Exception as exc:  # pragma: no cover - defensive guard
                return Err(InterpreterFailure(effect=effect, message=str(exc)))

    except StopIteration as stop:
        # Program completed, return final value
        # Generator[AllEffects, object, T] places T in StopIteration.value
        # Use explicit type narrowing pattern
        result: T = stop.value
        return Ok(result)


def unwrap_program_result(result: Result[T, InterpreterFailure]) -> T:
    """Convert a program Result into a value or raise for unexpected interpreter failures.

    This keeps API handlers simple while still enforcing typed error propagation
    from the interpreter boundary.
    """
    match result:
        case Ok(value):
            return value
        case Err(failure):
            raise RuntimeError(
                f"Interpreter failure for {type(failure.effect).__name__}: {failure.message}"
            )
