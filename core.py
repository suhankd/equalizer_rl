import numpy as np
import subprocess, os

from PySpice.Spice.Netlist import Circuit, SubCircuitFactory
from PySpice.Unit import *
import PySpice.Spice.NgSpice.Server as _NgSpiceServer
from PySpice.Spice.Parser import SpiceParser
from PySpice.Unit import *

import numpy as np
import matplotlib.pyplot as plt

PDK = "/home/royalewithcheese/.ciel/sky130A"

_PDK_NGSPICE_DIR = f"{PDK}/libs.tech/ngspice"

_PDK_LIB = f"{_PDK_NGSPICE_DIR}/sky130.lib.spice"

# Monkey-patch SpiceServer so ngspice runs from the PDK ngspice directory.
# This is required for sky130.lib.spice's relative .include paths to resolve.
def _patched_spice_call(self, spice_input):
    self._logger.info('Start the spice subprocess')
    process = subprocess.Popen(
        (self._spice_command, '-s'),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=_PDK_NGSPICE_DIR,  # key: lets ngspice resolve .lib relative includes
    )
    input_ = str(spice_input).encode('utf-8')
    stdout, stderr = process.communicate(input_)
    stderr = stderr.decode('utf-8')
    self._parse_stdout(stdout)
    number_of_points = self._parse_stderr(stderr)
    if number_of_points is None:
        raise NameError(
            'The number of points was not found in the standard error buffer,'
            + os.linesep + stderr
        )
    from PySpice.Spice.NgSpice.RawFile import RawFile
    return RawFile(stdout, number_of_points)

_NgSpiceServer.SpiceServer.__call__ = _patched_spice_call

def nfet(name, drain, gate, source, bulk, W=1, L=0.15, nf=1):
    W_um = W
    L_um = L
    return (
        f"X{name} {drain} {gate} {source} {bulk} "
        f"sky130_fd_pr__nfet_01v8 "
        f"L={L_um} W={W_um} nf={nf}\n"
    )


def pfet(name, drain, gate, source, bulk, W=1, L=0.15, nf=1):
    W_um = W
    L_um = L
    return (
        f"X{name} {drain} {gate} {source} {bulk} "
        f"sky130_fd_pr__pfet_01v8 "
        f"L={L_um} W={W_um} nf={nf}\n"
    )
