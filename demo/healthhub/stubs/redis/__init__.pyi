"""Type stubs for redis package."""

from typing import Optional, Union

class Redis:
    """Sync Redis client with strict typing."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: Optional[float] = None,
        socket_connect_timeout: Optional[float] = None,
        socket_keepalive: Optional[bool] = None,
        connection_pool: Optional[object] = None,
        encoding: str = "utf-8",
        encoding_errors: str = "strict",
        decode_responses: bool = False,
        retry_on_timeout: bool = False,
        ssl: bool = False,
        **kwargs: object,
    ) -> None: ...

    def publish(self, channel: str, message: Union[str, bytes]) -> int: ...
    def get(self, name: str) -> Optional[Union[str, bytes]]: ...
    def set(
        self,
        name: str,
        value: Union[str, bytes, int, float],
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> Optional[bool]: ...
    def delete(self, *names: str) -> int: ...
    def exists(self, *names: str) -> int: ...
    def close(self) -> None: ...
