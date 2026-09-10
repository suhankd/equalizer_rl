import core
globals().update(vars(core))

from dataclasses import dataclass


@dataclass
class CTLEParams:

    W: float = 99.6
    L: float = 0.15

    Rs: float = 250.0
    Cs: float = 10.0e-12

    Rd: float = 190.0
    Ibias: float = 1.25e-3