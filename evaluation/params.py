import core
globals().update(vars(core))

from dataclasses import dataclass

@dataclass
class CTLEParams:

    W: float = 99.6
    L: float = 0.15

    Rs: float = 230.0
    Cs: float = 9.5e-12

    Rd: float = 250.0
    Ibias: float = 1.25e-3

    dfe_coefficient: float = 0.045