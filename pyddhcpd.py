#!/usr/bin/env python3

from math import log
from itertools import cycle
from ipaddress import IPv4Address
import asyncio
import binascii
import struct
import socket, IN
import time
import io

import messages
from protocol import DDHCPProtocol
from ddhcp import DDHCP, BlockState
from lease import Lease
import dhcp
import dhcpoptions

from config import config

# TODO update_lease muss irgendwie extrahiert werden
# TODO brauchen wir TENTATIVE überhaupt?
# TODO irgendwann mal einen neuen Block claimen. Wann eigentlich?
# TODO config parameter n freie blöcke mindestens halten
# TODO Konfliktauflösug. Leases übermitteln
# TODO REQUEST forwarding
# TODO block_index may be outside permittable range
# TODO Split large packets automatically?
# TODO Block freigeben, wenn alle leases abgelaufen sind
# TODO DHCPProtocol in eigene Datei. unterverzeichnis dhcp?


class DHCPProtocol:
    def __init__(self, loop, ddhcp, config):
        self.loop = loop
        self.config = config
        self.ddhcp = ddhcp

    def connection_made(self, transport):
        self.transport = transport
        print("Connection made")

    def sendmsg(self, msg, addr):
        print("ans", msg)

        if addr[0] == '0.0.0.0' or msg.flags & 1:
            self.transport.sendto(msg.serialize(), ("<broadcast>", 68))
        else:
            self.transport.sendto(msg.serialize(), addr)

    def datagram_received(self, data, addr):
        # TODO verify packet somehow
        req = dhcp.DHCPPacket()
        req.deserialize(io.BytesIO(data))

        if req.op != req.BOOTREQUEST:
            return

        self.loop.create_task(self.handle_request(req, addr))

    @asyncio.coroutine
    def handle_request(self, req, addr):
        reqtype = next(filter(lambda o: o.__class__ == dhcpoptions.DHCPMessageType, req.options)).type

        print("req", req)

        msg = dhcp.DHCPPacket()
        msg.xid = req.xid
        msg.flags = req.flags
        msg.giaddr = req.giaddr
        msg.op = msg.BOOTREPLY
        msg.chaddr = req.chaddr
        msg.htype = 1

        now = time.time()

        if reqtype == dhcpoptions.DHCPMessageType.TYPES.DHCPDISCOVER:
            msg.options.append(dhcpoptions.DHCPMessageType(dhcpoptions.DHCPMessageType.TYPES.DHCPOFFER))

            try:
                lease = yield from self.ddhcp.get_lease(None, req.chaddr)
            except KeyError:
                return

            msg.yiaddr = lease.addr
            msg.options.append(dhcpoptions.IPAddressLeaseTime(lease.leasetime))

        elif reqtype == dhcpoptions.DHCPMessageType.TYPES.DHCPREQUEST:
            try:
                reqip = next(filter(lambda o: o.__class__ == dhcpoptions.RequestedIPAddress, req.options)).addr
            except StopIteration:
                reqip = req.ciaddr

            try:
                lease = yield from self.ddhcp.get_lease(reqip, req.chaddr)

                msg.options.append(dhcpoptions.DHCPMessageType(dhcpoptions.DHCPMessageType.TYPES.DHCPACK))
                msg.yiaddr = lease.addr
                msg.options.append(dhcpoptions.IPAddressLeaseTime(lease.leasetime))
                msg.options.append(dhcpoptions.SubnetMask(self.config["prefixlen"]))
                msg.options.append(dhcpoptions.RouterOption(lease.routers))
                msg.options.append(dhcpoptions.DomainNameServerOption(lease.dns))

            except KeyError:
                msg.options.append(dhcpoptions.DHCPMessageType(dhcpoptions.DHCPMessageType.TYPES.DHCPNAK))

        self.sendmsg(msg, addr)


def main():
    ddhcp = DDHCP(config)
    loop = asyncio.get_event_loop()


    # DHCP Socket

    def dhcp_factory():
        return DHCPProtocol(loop, ddhcp, config)

    dhcplisten = loop.create_datagram_endpoint(dhcp_factory, family=socket.AF_INET, local_addr=("0.0.0.0", 67))
    dhcptransport, dhcpprotocol = loop.run_until_complete(dhcplisten)

    sock = dhcptransport.get_extra_info("socket")

    sock.setsockopt(socket.SOL_SOCKET, IN.SO_BINDTODEVICE, bytes(config["clientif"] + '\0', "UTF-8"))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


    # DDHCP Socket

    def ddhcp_factory():
        return DDHCPProtocol(loop, (config["mcgroup"], config["mcport"]), ddhcp, config)

    listen = loop.create_datagram_endpoint(ddhcp_factory, family=socket.AF_INET6, local_addr=('::', config["mcport"]))
    transport, protocol = loop.run_until_complete(listen)

    sock = transport.get_extra_info("socket")

    ifn = socket.if_nametoindex(config["mcif"])
    ifn = struct.pack("I", ifn)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, ifn)

    # Join group
    group_bin = socket.inet_pton(socket.AF_INET6, config["mcgroup"])
    mreq = group_bin + ifn
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

    # Do not loopback multicast packets
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 0)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    dhcptransport.close()
    dhcploop.close()

    transport.close()
    loop.close()


if __name__ == '__main__':
    main()
