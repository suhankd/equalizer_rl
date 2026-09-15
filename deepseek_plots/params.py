import core
globals().update(vars(core))

from dataclasses import dataclass

@dataclass
class CTLEParams:

    W: float = 34.56
    L: float = 0.15

    Rs: float = 360.0
    Cs: float = 10.0e-12

    Rd: float = 445.0
    Ibias: float = 0.76e-3

    dfe_coefficient: float = 1/30.9