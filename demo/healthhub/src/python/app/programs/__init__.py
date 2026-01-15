"""Program execution layer.

This is Layer 2 in the 5-layer architecture:
Application programs (generators) → run_program → Composite Interpreter → Infrastructure
"""

from app.programs.runner import run_program, unwrap_program_result

__all__ = ["run_program", "unwrap_program_result"]
