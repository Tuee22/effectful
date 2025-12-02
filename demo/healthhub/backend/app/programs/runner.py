"""Program runner for effect execution.

Layer 2 in 5-layer architecture: Executes generator-based effect programs.
"""

from collections.abc import Generator
from typing import TypeVar

from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from typing import Protocol

T = TypeVar("T")


class InterpreterProtocol(Protocol):
    async def handle(self, effect: AllEffects) -> object: ...


async def run_program(
    program: Generator[AllEffects, object, T], interpreter: InterpreterProtocol
) -> T:
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
        Final program result

    Example:
        ```python
        def greet_patient(patient_id: UUID) -> Generator[AllEffects, object, str]:
            patient = yield GetPatientById(patient_id=patient_id)
            if patient is None:
                return "Patient not found"
            return f"Hello {patient.first_name}!"

        result = await run_program(greet_patient(patient_id), interpreter)
        ```
    """
    effect_result: object = None

    try:
        while True:
            # Step program: send previous result, receive next effect
            effect = program.send(effect_result)

            # Execute effect via interpreter
            effect_result = await interpreter.handle(effect)

    except StopIteration as stop:
        # Program completed, return final value
        # Generator[AllEffects, object, T] places T in StopIteration.value
        # Use explicit type narrowing pattern
        result: T = stop.value
        return result
