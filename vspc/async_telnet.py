# Copyright (c) 2001-2016 Python Software Foundation
# Copyright (c) 2017 VMware Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Telnet client class using asyncio.
Based on the standard telnetlib module from Python3.
"""
import asyncio

# Telnet protocol characters (don't change)
IAC = bytes([255])  # "Interpret As Command"
DONT = bytes([254])
DO = bytes([253])
WONT = bytes([252])
WILL = bytes([251])
theNULL = bytes([0])
SE = bytes([240])  # Subnegotiation End
NOP = bytes([241])  # No Operation
SB = bytes([250])  # Subnegotiation Begin
NOOPT = bytes([0])


class AsyncTelnet:
    def __init__(self, reader, opt_handler):
        self._reader = reader
        self._opt_handler = opt_handler
        self.rawq = b''
        self.irawq = 0
        self.cookedq = b''
        self.eof = 0
        self.iacseq = b''  # Buffer for IAC sequence.
        self.sb = 0  # flag for SB and SE sequence.
        self.sbdataq = b''

    @asyncio.coroutine
    def process_rawq(self):
        """Transfer from raw queue to cooked queue.

        Set self.eof when connection is closed.
        """
        buf = [b'', b'']
        try:
            while self.rawq:
                c = yield from self.rawq_getchar()
                if not self.iacseq:
                    if self.sb == 0 and c == theNULL:
                        continue
                    if self.sb == 0 and c == b"\021":
                        continue
                    if c != IAC:
                        buf[self.sb] = buf[self.sb] + c
                        continue
                    else:
                        self.iacseq += c
                elif len(self.iacseq) == 1:
                    # 'IAC: IAC CMD [OPTION only for WILL/WONT/DO/DONT]'
                    if c in (DO, DONT, WILL, WONT):
                        self.iacseq += c
                        continue

                    self.iacseq = b''
                    if c == IAC:
                        buf[self.sb] = buf[self.sb] + c
                    else:
                        if c == SB:  # SB ... SE start.
                            self.sb = 1
                            self.sbdataq = b''
                        elif c == SE:
                            self.sb = 0
                            self.sbdataq = self.sbdataq + buf[1]
                            buf[1] = b''
                        yield from self._opt_handler(c, NOOPT,
                                                     data=self.sbdataq)
                elif len(self.iacseq) == 2:
                    cmd = self.iacseq[1:2]
                    self.iacseq = b''
                    opt = c
                    if cmd in (DO, DONT):
                        yield from self._opt_handler(cmd, opt)
                    elif cmd in (WILL, WONT):
                        yield from self._opt_handler(cmd, opt)
        except EOFError:  # raised by self.rawq_getchar()
            self.iacseq = b''  # Reset on EOF
            self.sb = 0
            pass
        self.cookedq = self.cookedq + buf[0]
        self.sbdataq = self.sbdataq + buf[1]

    @asyncio.coroutine
    def rawq_getchar(self):
        """Get next char from raw queue.

        Raise EOFError when connection is closed.
        """
        if not self.rawq:
            yield from self.fill_rawq()
            if self.eof:
                raise EOFError
        c = self.rawq[self.irawq:self.irawq + 1]
        self.irawq = self.irawq + 1
        if self.irawq >= len(self.rawq):
            self.rawq = b''
            self.irawq = 0
        return c

    @asyncio.coroutine
    def fill_rawq(self):
        """Fill raw queue from exactly one recv() system call.

        Set self.eof when connection is closed.
        """
        if self.irawq >= len(self.rawq):
            self.rawq = b''
            self.irawq = 0
        # The buffer size should be fairly small so as to avoid quadratic
        # behavior in process_rawq() above
        buf = yield from self._reader.read(50)
        self.eof = (not buf)
        self.rawq = self.rawq + buf

    @asyncio.coroutine
    def read_some(self):
        """Read at least one byte of cooked data unless EOF is hit.

        Return b'' if EOF is hit.
        """
        yield from self.process_rawq()
        while not self.cookedq and not self.eof:
            yield from self.fill_rawq()
            yield from self.process_rawq()
        buf = self.cookedq
        self.cookedq = b''
        return buf
