"""Type stubs for pydantic-settings to eliminate Any types."""

from typing import ClassVar, Dict, Optional
from pydantic import BaseModel

class SettingsConfigDict(Dict[str, object]):
    """Pydantic settings configuration dictionary with strict typing."""

    env_file: Optional[str]
    case_sensitive: bool
    env_prefix: str

class BaseSettings(BaseModel):
    """Pydantic BaseSettings with strict typing, no Any types."""

    model_config: ClassVar[SettingsConfigDict]
