"""Type stubs for botocore.exceptions.

Minimal stubs for botocore exceptions to satisfy mypy strict mode.
"""

class ClientError(Exception):
    """AWS client error with response details."""

    response: dict[str, dict[str, str]]

    def __init__(self, error_response: dict[str, dict[str, str]], operation_name: str) -> None: ...
