from enum import Enum
from typing import Any, Optional

import pydantic


class StrEnum(str, Enum):
    def _generate_next_value_(name, *_):
        return name


class BaseModelStrict(pydantic.BaseModel):
    @classmethod
    def get_properties(cls):
        return [
            prop for prop in cls.__dict__ if isinstance(cls.__dict__[prop], property)
        ]

    def dict(
        self,
        *,
        include: Optional[Any] = None,
        exclude: Optional[Any] = None,
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """Override the dict function to include our properties"""

        attribs = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        props = self.get_properties()

        # Include and exclude properties
        if include:
            props = [prop for prop in props if prop in include]
        if exclude:
            props = [prop for prop in props if prop not in exclude]

        # Update the attribute dict with the properties
        if props:
            attribs.update({prop: getattr(self, prop) for prop in props})
        return attribs

    class Config:
        allow_mutation = False
        use_enum_values = True
