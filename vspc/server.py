#!/usr/bin/env python3
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

import asyncio
import functools
import os
import ssl
import sys

from oslo_config import cfg
from oslo_log import log as logging

from vspc import async_telnet
from vspc.async_telnet import IAC, SB, SE, DO, DONT, WILL, WONT

opts = [
    cfg.StrOpt('host',
               default='0.0.0.0',
               help='Host on which to listen for incoming requests'),
    cfg.IntOpt('port',
               default=13370,
               help='Port on which to listen for incoming requests'),
    cfg.StrOpt('cert', help='SSL certificate file'),
    cfg.StrOpt('key', help='SSL key file (if separate from cert)'),
    cfg.StrOpt('uri', help='VSPC URI'),
    cfg.StrOpt('serial_log_dir', help='The directory where serial logs are '
                                      'saved'),
    ]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)

BINARY = bytes([0])  # 8-bit data path
SGA = bytes([3])  # suppress go ahead
VMWARE_EXT = bytes([232])

KNOWN_SUBOPTIONS_1 = bytes([0])
KNOWN_SUBOPTIONS_2 = bytes([1])
VMOTION_BEGIN = bytes([40])
VMOTION_GOAHEAD = bytes([41])
VMOTION_NOTNOW = bytes([43])
VMOTION_PEER = bytes([44])
VMOTION_PEER_OK = bytes([45])
VMOTION_COMPLETE = bytes([46])
VMOTION_ABORT = bytes([48])
VM_VC_UUID = bytes([80])
GET_VM_VC_UUID = bytes([81])
VM_NAME = bytes([82])
GET_VM_NAME = bytes([83])
DO_PROXY = bytes([70])
WILL_PROXY = bytes([71])
WONT_PROXY = bytes([73])

SUPPORTED_OPTS = (KNOWN_SUBOPTIONS_1 + KNOWN_SUBOPTIONS_2 + VMOTION_BEGIN +
                  VMOTION_GOAHEAD + VMOTION_NOTNOW + VMOTION_PEER +
                  VMOTION_PEER_OK + VMOTION_COMPLETE + VMOTION_ABORT +
                  VM_VC_UUID + GET_VM_VC_UUID + VM_NAME + GET_VM_NAME +
                  DO_PROXY + WILL_PROXY + WONT_PROXY)


class VspcServer(object):
    def __init__(self):
        self.sock_to_uuid = dict()

    @asyncio.coroutine
    def handle_known_suboptions(self, writer, data):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        LOG.debug("<< %s KNOWN-SUBOPTIONS-1 %s", peer, data)
        LOG.debug(">> %s KNOWN-SUBOPTIONS-2 %s", peer, SUPPORTED_OPTS)
        writer.write(IAC + SB + VMWARE_EXT + KNOWN_SUBOPTIONS_2 +
                     SUPPORTED_OPTS + IAC + SE)
        LOG.debug(">> %s GET-VM-VC-UUID", peer)
        writer.write(IAC + SB + VMWARE_EXT + GET_VM_VC_UUID + IAC + SE)
        yield from writer.drain()

    @asyncio.coroutine
    def handle_do_proxy(self, writer, data):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        dir, uri = data[0], data[1:].decode('ascii')
        LOG.debug("<< %s DO-PROXY %c %s", peer, dir, uri)
        if chr(dir) != 'S' or uri != CONF.uri:
            LOG.debug(">> %s WONT-PROXY", peer)
            writer.write(IAC + SB + VMWARE_EXT + WONT_PROXY + IAC + SE)
            yield from writer.drain()
            writer.close()
        else:
            LOG.debug(">> %s WILL-PROXY", peer)
            writer.write(IAC + SB + VMWARE_EXT + WILL_PROXY + IAC + SE)
            yield from writer.drain()

    def handle_vm_vc_uuid(self, socket, data):
        peer = socket.getpeername()
        uuid = data.decode('ascii')
        LOG.debug("<< %s VM-VC-UUID %s", peer, uuid)
        uuid = uuid.replace(' ', '')
        self.sock_to_uuid[socket] = uuid

    @asyncio.coroutine
    def handle_vmotion_begin(self, writer, data):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        LOG.debug("<< %s VMOTION-BEGIN %s", peer, data)
        secret = os.urandom(4)
        LOG.debug(">> %s VMOTION-GOAHEAD %s %s", peer, data, secret)
        writer.write(IAC + SB + VMWARE_EXT + VMOTION_GOAHEAD +
                     data + secret + IAC + SE)
        yield from writer.drain()

    @asyncio.coroutine
    def handle_vmotion_peer(self, writer, data):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        LOG.debug("<< %s VMOTION-PEER %s", peer, data)
        LOG.debug("<< %s VMOTION-PEER-OK %s", peer, data)
        writer.write(IAC + SB + VMWARE_EXT + VMOTION_PEER_OK + data + IAC + SE)
        yield from writer.drain()

    def handle_vmotion_complete(self, socket, data):
        peer = socket.getpeername()
        LOG.debug("<< %s VMOTION-COMPLETE %s", peer, data)

    @asyncio.coroutine
    def handle_do(self, writer, opt):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        LOG.debug("<< %s DO %s", peer, opt)
        if opt in (BINARY, SGA):
            LOG.debug(">> %s WILL", peer)
            writer.write(IAC + WILL + opt)
            yield from writer.drain()
        else:
            LOG.debug(">> %s WONT", peer)
            writer.write(IAC + WONT + opt)
            yield from writer.drain()

    @asyncio.coroutine
    def handle_will(self, writer, opt):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        LOG.debug("<< %s WILL %s", peer, opt)
        if opt in (BINARY, SGA, VMWARE_EXT):
            LOG.debug(">> %s DO", peer)
            writer.write(IAC + DO + opt)
            yield from writer.drain()
        else:
            LOG.debug(">> %s DONT", peer)
            writer.write(IAC + DONT + opt)
            yield from writer.drain()

    @asyncio.coroutine
    def option_handler(self, cmd, opt, writer, data=None):
        socket = writer.get_extra_info('socket')
        if cmd == SE and data[0:1] == VMWARE_EXT:
            vmw_cmd = data[1:2]
            if vmw_cmd == KNOWN_SUBOPTIONS_1:
                yield from self.handle_known_suboptions(writer, data[2:])
            elif vmw_cmd == DO_PROXY:
                yield from self.handle_do_proxy(writer, data[2:])
            elif vmw_cmd == VM_VC_UUID:
                self.handle_vm_vc_uuid(socket, data[2:])
            elif vmw_cmd == VMOTION_BEGIN:
                yield from self.handle_vmotion_begin(writer, data[2:])
            elif vmw_cmd == VMOTION_PEER:
                yield from self.handle_vmotion_peer(writer, data[2:])
            elif vmw_cmd == VMOTION_COMPLETE:
                self.handle_vmotion_complete(socket, data[2:])
            else:
                LOG.error("Unknown VMware cmd: %s %s", vmw_cmd, data[2:])
                writer.close()
        elif cmd == DO:
            yield from self.handle_do(writer, opt)
        elif cmd == WILL:
            yield from self.handle_will(writer, opt)

    def save_to_log(self, uuid, data):
        fpath = os.path.join(CONF.serial_log_dir, uuid)
        with open(fpath, 'ab') as f:
            f.write(data)

    @asyncio.coroutine
    def handle_telnet(self, reader, writer):
        opt_handler = functools.partial(self.option_handler, writer=writer)
        telnet = async_telnet.AsyncTelnet(reader, opt_handler)
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        LOG.info("%s connected", peer)
        data = yield from telnet.read_some()
        uuid = self.sock_to_uuid.get(socket)
        if uuid is None:
            LOG.error("%s didn't present UUID", peer)
            writer.close()
            return
        try:
            while data:
                self.save_to_log(uuid, data)
                data = yield from telnet.read_some()
        finally:
            self.sock_to_uuid.pop(socket, None)
        LOG.info("%s disconnected", peer)
        writer.close()

    def start(self):
        loop = asyncio.get_event_loop()
        ssl_context = None
        if CONF.cert:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            ssl_context.load_cert_chain(certfile=CONF.cert, keyfile=CONF.key)
        coro = asyncio.start_server(self.handle_telnet,
                                    CONF.host,
                                    CONF.port,
                                    ssl=ssl_context,
                                    loop=loop)
        server = loop.run_until_complete(coro)

        # Serve requests until Ctrl+C is pressed
        LOG.info("Serving on %s", server.sockets[0].getsockname())
        LOG.info("Log directory: %s", CONF.serial_log_dir)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

        # Close the server
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()


def main():
    logging.register_options(CONF)
    CONF(sys.argv[1:], prog='vspc')
    logging.setup(CONF, "vspc")
    if not CONF.serial_log_dir:
        LOG.error("serial_log_dir is not specified")
        sys.exit(1)
    if not os.path.exists(CONF.serial_log_dir):
        LOG.info("Creating log directory: %s", CONF.serial_log_dir)
        os.makedirs(CONF.serial_log_dir)
    srv = VspcServer()
    srv.start()


if __name__ == '__main__':
    main()
