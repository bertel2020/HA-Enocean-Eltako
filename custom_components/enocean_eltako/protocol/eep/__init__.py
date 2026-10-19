"""EEP codecs. Every profile is addressed as EEP plus variant ("std" or "eltako")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Variant = Literal["std", "eltako"]


@dataclass(frozen=True, slots=True, order=True)
class EEPRef:
    """An EEP together with its variant, written "A5-08-01:eltako" in config data."""

    eep: str
    variant: Variant

    def __str__(self) -> str:
        return f"{self.eep}:{self.variant}"

    @classmethod
    def parse(cls, text: str) -> EEPRef:
        eep, _, variant = text.partition(":")
        if variant not in ("std", "eltako"):
            raise ValueError(f"EEP reference needs a variant: {text!r}")
        return cls(eep.upper(), variant)  # type: ignore[arg-type]
