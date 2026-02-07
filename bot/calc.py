from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineItem:
    section: str
    title: str
    area: float
    price_per_m2: float

    @property
    def cost(self) -> float:
        return self.area * self.price_per_m2


def roof_area(area: float, roof_coef: float) -> float:
    return area * roof_coef
