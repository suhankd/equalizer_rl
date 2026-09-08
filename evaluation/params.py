import core
globals().update(vars(core))

from dataclasses import dataclass


@dataclass
class CTLEParams:

    W: float = 100.0
    L: float = 0.15

    Rs: float = 80.0
    Cs: float = 1.2e-12

    Rd: float = 100.0
    Ibias: float = 1.5e-3