import numpy as np
import logging
from engineering_notation import EngNumber  # only from pip
import atexit
import struct

logger = logging.getLogger(__name__)


class AEDat2Output:
    '''
    outputs AEDAT-2.0 jAER format DVS data from v2e
    '''

    def __init__(self, filepath: str):
        self.filepath = filepath
        # edit below to match your device from https://inivation.com/support/software/fileformat/#aedat-20
        CAMERA = 'Davis346BMono'  # edit for your desired output
        if CAMERA == 'Davis346BMono':
            # DAVIS
            # In the 32-bit address:
            # bit 32 (1-based) being 1 indicates an APS sample
            # bit 11 (1-based) being 1 indicates a special event
            # bits 11 and 32 (1-based) both being zero signals a polarity event
            self.yShiftBits = 22
            self.xShiftBits = 12
            self.polShiftBits = 11  # see https://inivation.com/support/software/fileformat/#aedat-20
            self.sizex = 346
            self.sizey = 260
            self.flipy = True  # v2e uses computer vision matrix printing convention of UL pixel being 0,0, but jAER uses original graphics and graphing convention that 0,0 is LL
            self.flipx = False
        else:
            raise Exception('CAMERA type not found, add your camera to {}'.format(__name__))

        self.numEventsWritten = 0
        logging.info('opening AEDAT-2.0 output file {} in binary mode'.format(filepath))
        self.file = open(filepath, 'wb')
        self._writeHeader()
        atexit.register(self.cleanup)

    def cleanup(self):
        if self.file:
            logger.info("Closing {} after writing {} events".format(self.filepath, EngNumber(self.numEventsWritten)))
            self.file.close()

    def close(self):
        if self.file:
            self.file.close()
            self.file = None

    def _writeHeader(self):
        import datetime, time, getpass
        # CRLF \r\n is needed to not break header parsing in jAER
        date = datetime.datetime.now().strftime('# Creation time: %I:%M%p %B %d %Y\r\n')  # Tue Jan 26 13:57:06 CET 2016
        time = '# Creation time: System.currentTimeMillis() {}\r\n'.format(int(time.time() * 1000.))
        user = '# User name: {}\r\n'.format(getpass.getuser())
        header = ('#!AER-DAT2.0\r\n',
                  '# This is a raw AE data file created by AEDat2Output in v2e (see https://github.com/SensorsINI/v2e)\r\n',
                  '# Data format is int32 address, int32 timestamp (8 bytes total), repeated for each event\r\n',
                  '# Timestamps tick is 1 us\r\n',
                  date, time,
                  user
                  )
        for s in header:
            bytes = s.encode('UTF-8')
            self.file.write(bytes)

    def appendEvents(self, events: np.ndarray):
        if self.file is None:
            raise Exception('output file closed already')

        if len(events) == 0:
            return
        n = events.shape[0]
        t = (1e6 * events[:, 0]).astype(np.int32)
        x = events[:, 1].astype(np.int32)
        if self.flipx: x = (self.sizex - 1) - x  # 0 goes to sizex-1
        y = events[:, 2].astype(np.int32)
        if self.flipy: y = (self.sizey - 1) - y
        p = ((events[:, 3] + 1) / 2).astype(np.int32)
        a = (x << self.xShiftBits | y << self.yShiftBits | p << self.polShiftBits)
        out = np.empty(2 * n, dtype=np.int32)
        out[0::2] = a  # addresses even
        out[1::2] = t  # timestamps odd
        # now out is numpy array holding int32 timestamp,address array, i.e. ts0, ad0, ts1, ad1, etc
        self.file.write(out.byteswap().tobytes(order='C'))  # java is big-endian, so  byteswap to get this
        self.numEventsWritten += n
        self.file.flush()
        # logger.info('wrote {} events'.format(n))

# class AEDat2OutputTest():
#     f = AEDat2Output('aedattest.aedat')
#     e = [[0., 0, 0, 0], [1e-6, 0, 0, 1], [2e-6, 1, 0, 0]]
#     ne = np.array(e)
#     f.appendEvents(ne)
#     f.close()