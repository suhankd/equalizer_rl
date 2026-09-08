import core
globals().update(vars(core))

class ctle(SubCircuitFactory):

    NAME = 'ctle'
    NODES = ('vinp', 'vinn', 'voutp', 'voutn', 'vdd')

    def __init__(
        self,
        W=10,
        L=0.18,
        Rs=175,
        Cs=1.9e-12,
        Rd=400,
        Ibias=100e-3
    ):

        super().__init__()

        self.raw_spice += nfet(
            '1',
            'voutp',
            'vinp',
            'src_p',
            '0',
            W=W,
            L=L
        )

        self.raw_spice += nfet(
            '2',
            'voutn',
            'vinn',
            'src_n',
            '0',
            W=W,
            L=L
        )

        self.R(
            'S',
            'src_p',
            'src_n',
            Rs
        )

        self.C(
            'S',
            'src_p',
            'src_n',
            Cs
        )

        self.R(
            'Rdp',
            'vdd',
            'voutp',
            Rd
        )

        self.R(
            'Rdn',
            'vdd',
            'voutn',
            Rd
        )

        self.I(
            'biasp',
            'src_p',
            '0',
            Ibias
        )

        self.I(
            'biasn',
            'src_n',
            '0',
            Ibias
        )