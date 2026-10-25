"""Bounded exact numeric tokens. No binary floats or exponent expansion in evidence."""

import re
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, model_validator

from otarchguard.diagnostics import check_limit, fail
from otarchguard.domain import Record

NUMERIC_CHARACTERS = 64
NUMERIC_EXPONENT = 9999
_GRAMMAR = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", re.ASCII)


def _valid(token: str) -> bool:
    if len(token) > NUMERIC_CHARACTERS or _GRAMMAR.fullmatch(token) is None:
        return False
    exponent = re.split("[eE]", token)
    return len(exponent) == 1 or abs(int(exponent[1])) <= NUMERIC_EXPONENT


class NumericToken(Record):
    """Source number category and exact lexeme, serialized as a tagged JSON object."""

    numeric_token: str = Field(min_length=1, max_length=NUMERIC_CHARACTERS)
    numeric_category: Literal["integer", "number"]

    @model_validator(mode="after")
    def validate_token(self) -> Self:
        category = "number" if any(c in self.numeric_token for c in ".eE") else "integer"
        if not _valid(self.numeric_token) or category != self.numeric_category:
            raise ValueError("Invalid bounded numeric token/category")
        return self


def parse_number(token: str, maximum: int = NUMERIC_CHARACTERS) -> int | NumericToken:
    check_limit("numeric_token_characters", len(token), min(maximum, NUMERIC_CHARACTERS))
    if not _valid(token):
        fail("IMPORT_NUMERIC_TOKEN", "$", "Invalid number or exponent outside -9999..9999.")
    category: Literal["integer", "number"] = (
        "number" if any(c in token for c in ".eE") else "integer"
    )
    if category == "integer" and token != "-0":
        return int(token)  # Canonical JSON integers are lossless; -0 needs its lexeme.
    return NumericToken(numeric_token=token, numeric_category=category)


def numeric_text(value: int | NumericToken) -> str:
    return value.numeric_token if isinstance(value, NumericToken) else str(value)


def excel_magnitude_ambiguous(value: int | NumericToken) -> bool:
    """Compare exact decimals without arithmetic, rounding or exponent expansion.

    This checks Excel's normal finite range, not the original user's input.
    Temporary Decimal values never enter Pydantic/evidence/native models.
    """
    number = Decimal(numeric_text(value)).copy_abs()
    return not number.is_zero() and not (
        Decimal("2.2250738585072014e-308") <= number <= Decimal("1.7976931348623157e308")
    )
