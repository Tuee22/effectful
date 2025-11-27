"""Type stubs for pydantic to eliminate Any types."""

from typing import (
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    Callable,
)
from datetime import datetime

T = TypeVar("T", bound="BaseModel")

class ConfigDict(Dict[str, object]):
    """Pydantic configuration dictionary with strict typing."""

    pass

class BaseModel:
    """Pydantic BaseModel with strict typing, no Any types."""

    def __init__(self, **data: object) -> None: ...
    @classmethod
    def model_validate(cls: Type[T], obj: object) -> T: ...
    @classmethod
    def model_validate_json(cls: Type[T], json_data: Union[str, bytes]) -> T: ...
    def model_dump(
        self,
        include: Optional[Union[set[str], Dict[str, object]]] = None,
        exclude: Optional[Union[set[str], Dict[str, object]]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
        mode: Literal["python", "json"] = "python",
    ) -> Dict[str, object]: ...
    def model_dump_json(
        self,
        include: Optional[Union[set[str], Dict[str, object]]] = None,
        exclude: Optional[Union[set[str], Dict[str, object]]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
    ) -> str: ...
    @classmethod
    def model_rebuild(cls) -> None: ...
    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = "#/$defs/{model}",
        schema_generator: Optional[object] = None,
        mode: Literal["serialization", "validation"] = "serialization",
    ) -> Dict[str, object]: ...

    model_config: ClassVar[ConfigDict]

class ValidationError(ValueError):
    """Pydantic validation error."""

    def __init__(self, errors: List[Dict[str, object]]) -> None: ...
    errors: List[Dict[str, object]]

# Field function with generic typing
_FieldT = TypeVar("_FieldT")

def Field(
    default: _FieldT = ...,
    default_factory: Optional[Callable[[], _FieldT]] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    examples: Optional[List[object]] = None,
    exclude: Optional[bool] = None,
    include: Optional[bool] = None,
    discriminator: Optional[str] = None,
    json_schema_extra: Optional[
        Union[Dict[str, object], Callable[[Dict[str, object]], None]]
    ] = None,
    frozen: Optional[bool] = None,
    validate_default: Optional[bool] = None,
    repr: bool = True,
    init_var: Optional[bool] = None,
    kw_only: Optional[bool] = None,
    pattern: Optional[str] = None,
    strict: Optional[bool] = None,
    gt: Optional[Union[int, float]] = None,
    ge: Optional[Union[int, float]] = None,
    lt: Optional[Union[int, float]] = None,
    le: Optional[Union[int, float]] = None,
    multiple_of: Optional[Union[int, float]] = None,
    allow_inf_nan: Optional[bool] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    **kwargs: object,
) -> _FieldT: ...

# Field validators
_ValidatorT = TypeVar("_ValidatorT")

def field_validator(
    *fields: str, mode: str = "before", check_fields: Optional[bool] = None
) -> Callable[[Callable[..., _ValidatorT]], Callable[..., _ValidatorT]]: ...

# Email validation
class EmailStr(str):
    """Email string type."""

    pass
