from pipython import GCSDevice, pitools
from random import uniform
STAGES = ['L-511.44AD00', 'L-511.44AD00', 'NOSTAGE', 'NOSTAGE']
REFMODE = ['FNL', 'FNL']
with GCSDevice('C-884') as pidevice:
    pidevice.ConnectUSB(serialnum='118078756')
    pitools.startup(pidevice, stages=STAGES,refmodes=REFMODE)
    # print('connected: {}'.format(pidevice.qIDN().strip()))
    # print(pidevice.qPOS())
    # rangemin = list(pidevice.qTMN().values())
    # rangemax = list(pidevice.qTMX().values())
    # ranges = zip(rangemin, rangemax)
    # targets = [uniform(rmin, rmax) for (rmin, rmax) in ranges]
    pidevice.MOV(pidevice.axes,[60.001,60])
    print(pidevice.qPOS())