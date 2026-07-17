"""Pydantic request/response models for the prediction API."""
from pydantic import BaseModel, EmailStr, Field, validator

from .config import (
    DEFAULT_MAX_SEQUENCES,
    DEFAULT_TOTAL_LENGTH,
    DEFAULT_VARIANT_LENGTH,
    MAX_TOTAL_LENGTH,
)


class InputData(BaseModel):
    amino_acid_sequence: str
    email: EmailStr = None
    max_sequences: int = Field(default=DEFAULT_MAX_SEQUENCES, ge=1, le=1e16)
    variant_length: int = Field(default=DEFAULT_VARIANT_LENGTH, ge=1, le=30)
    total_length: int = Field(default=DEFAULT_TOTAL_LENGTH, ge=5, le=MAX_TOTAL_LENGTH)
    prefix: str = None  # New field
    suffix: str = None  # New field

    @validator('total_length')
    def validate_total_length(cls, v, values):
        if ('prefix' in values and values['prefix'] is not None and
            'suffix' in values and values['suffix'] is not None):
            return v

        # Apply normal validation for default sequences
        if 'variant_length' in values and v != 0 and v < values['variant_length'] + 2:
            raise ValueError(f"Total length must be at least variant_length + 2 (got {v} < {values['variant_length']} + 2)")

        return v

    @validator('prefix', 'suffix')
    def validate_sequences(cls, v, values):
        if v is not None:
            # Check if sequence contains only valid DNA bases
            if not all(base in 'ATGC' for base in v.upper()):
                raise ValueError("Sequence must contain only A, T, G, C bases")
        return v.upper() if v else v
