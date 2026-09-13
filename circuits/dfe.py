import core
globals().update(vars(core))

class dfe(SubCircuitFactory):

    NAME = 'dfe'

    NODES = (
        'inp',
        'inn',
        'ck',
        'ckb',
        'vdd',
        'outp',
        'outn'
    )

    def __init__(
        self,
        W=5,
        L=0.15,
        nf=5,
        Rsense=500,
        Cchannel=50e-15,
        Rfb_top=9e3,
        Rfb_bottom=1e3,
        I_tail1=300e-6,
        I_tail2=150e-6
    ):

        super().__init__()

        # -----------------------------------------------------
        # ISI CHANNEL
        #
        # inp -> ch_p
        # inn -> ch_n
        #
        # Kept here because your original DFE testbench
        # includes the channel before the summer.
        # -----------------------------------------------------

        self.R(
            'ch_p',
            'inp',
            'ch_p',
            Rsense
        )

        self.C(
            'ch_p',
            'ch_p',
            self.gnd,
            Cchannel
        )

        self.R(
            'ch_n',
            'inn',
            'ch_n',
            Rsense
        )

        self.C(
            'ch_n',
            'ch_n',
            self.gnd,
            Cchannel
        )

        # -----------------------------------------------------
        # LOAD RESISTORS
        # -----------------------------------------------------

        self.raw_spice += f"""
Xload1 A vdd {self.gnd} sky130_fd_pr__res_high_po
+ W=1.41u L=4.4u mult=1 m=1

Xload2 B vdd {self.gnd} sky130_fd_pr__res_high_po
+ W=1.41u L=4.4u mult=1 m=1
"""

        # -----------------------------------------------------
        # SUMMER PAIR
        # -----------------------------------------------------

        self.raw_spice += f"""
XM1 A ch_p iss1_node {self.gnd}
+ sky130_fd_pr__nfet_01v8
+ L={L}
+ W={W}
+ nf={nf}
+ ad='int((nf+1)/2) * W/nf * 0.29'
+ as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)'
+ ps='2*int((nf+2)/2) * (W/nf + 0.29)'
+ nrd='0.29 / W'
+ nrs='0.29 / W'
+ sa=0 sb=0 sd=0
+ mult=1 m=1

XM2 B ch_n iss1_node {self.gnd}
+ sky130_fd_pr__nfet_01v8
+ L={L}
+ W={W}
+ nf={nf}
+ ad='int((nf+1)/2) * W/nf * 0.29'
+ as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)'
+ ps='2*int((nf+2)/2) * (W/nf + 0.29)'
+ nrd='0.29 / W'
+ nrs='0.29 / W'
+ sa=0 sb=0 sd=0
+ mult=1 m=1
"""

        # -----------------------------------------------------
        # FEEDBACK ATTENUATOR
        #
        # coefficient = Rfb_bottom /
        #               (Rfb_top + Rfb_bottom)
        #
        # 1k / (9k + 1k) = 0.1
        # -----------------------------------------------------

        self.R(
            'fb_p1',
            'fb_p',
            'fb_pa',
            Rfb_top
        )

        self.R(
            'fb_p2',
            'fb_pa',
            self.gnd,
            Rfb_bottom
        )

        self.R(
            'fb_n1',
            'fb_n',
            'fb_na',
            Rfb_top
        )

        self.R(
            'fb_n2',
            'fb_na',
            self.gnd,
            Rfb_bottom
        )

        # -----------------------------------------------------
        # FEEDBACK PAIR
        # -----------------------------------------------------

        self.raw_spice += f"""
XM3 A fb_pa iss2_node {self.gnd}
+ sky130_fd_pr__nfet_01v8
+ L={L}
+ W={W}
+ nf={nf}
+ ad='int((nf+1)/2) * W/nf * 0.29'
+ as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)'
+ ps='2*int((nf+2)/2) * (W/nf + 0.29)'
+ nrd='0.29 / W'
+ nrs='0.29 / W'
+ sa=0 sb=0 sd=0
+ mult=1 m=1

XM4 B fb_na iss2_node {self.gnd}
+ sky130_fd_pr__nfet_01v8
+ L={L}
+ W={W}
+ nf={nf}
+ ad='int((nf+1)/2) * W/nf * 0.29'
+ as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)'
+ ps='2*int((nf+2)/2) * (W/nf + 0.29)'
+ nrd='0.29 / W'
+ nrs='0.29 / W'
+ sa=0 sb=0 sd=0
+ mult=1 m=1
"""

        # -----------------------------------------------------
        # TAIL CURRENTS
        # -----------------------------------------------------

        self.I(
            'SS1',
            'iss1_node',
            self.gnd,
            I_tail1
        )

        self.I(
            'SS2',
            'iss2_node',
            self.gnd,
            I_tail2
        )

        # -----------------------------------------------------
        # LATCH 1
        #
        # Determines current data.
        # -----------------------------------------------------

        self.raw_spice += """
Xlatch1 A B outp_l1 outn_l1 ck ckb vdd cml_latch
"""

        # -----------------------------------------------------
        # LATCH 2
        #
        # Stores previous decision for feedback.
        # -----------------------------------------------------

        self.raw_spice += """
Xlatch2 outp_l1 outn_l1 fb_p fb_n ckb ck vdd cml_latch
"""

        # -----------------------------------------------------
        # OUTPUT
        #
        # Latch 2 output is the stored previous decision.
        # -----------------------------------------------------

        self.raw_spice += """
Eoutp outp 0 VALUE = {V(fb_p)}
Eoutn outn 0 VALUE = {V(fb_n)}
"""