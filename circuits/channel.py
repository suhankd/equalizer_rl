class channel_section(SubCircuitFactory):

    NAME = 'channel_section'
    NODES = ('t_in', 't_out')

    def __init__(self):
        super().__init__()

        self.R('1', 't_in', 'n2', 5.55)
        self.L('1', 't_in', 'n2', '470p')

        self.R('2', 'n2', 'n26', '2k')
        self.R('3', 'n2', 'n27', '1k')

        self.C('1', 'n26', self.gnd, '0.2p')
        self.C('2', 'n27', self.gnd, '0.08p')

        self.L('2', 'n2', 't_out', '1n')
        self.C('3', 't_out', self.gnd, '0.039p')
        
        
class channel(SubCircuitFactory):

    NAME = 'channel'
    NODES = ('INPUT', 'OUTPUT')

    def __init__(self, n_sections = 8):

        super().__init__()

        input_node = 'INPUT'

        for i in range(n_sections):

            if i == n_sections - 1:

                next_node = 'OUTPUT'

            else:

                next_node = f'ch{i+1}'

            self.X(f'S{i+1}', 'channel_section', input_node, next_node)

            input_node = next_node
