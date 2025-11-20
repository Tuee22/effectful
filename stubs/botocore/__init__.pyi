"""Type stubs for botocore.

Minimal stubs for the botocore library to satisfy mypy strict mode.
Only includes types actually used by effectful.
"""

# Re-export exceptions
from botocore.exceptions import ClientError as ClientError
