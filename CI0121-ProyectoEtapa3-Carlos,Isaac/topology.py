#!/usr/bin/env python3
"""
Topologia Mininet para el proyecto de cache DNS en P4.

Hosts:
    h1, h2, h3, h4 -> clientes DNS (10.0.0.1 - 10.0.0.4)
    h5 -> servidor DNS real (10.0.0.5)
    s1 -> switch P4 corriendo dns_cache.json sobre simple_switch

Ejecutar con: sudo python3 topology.py
"""

import os
import time

from mininet.net import Mininet
from mininet.node import Switch
from mininet.cli import CLI
from mininet.log import setLogLevel, info


class P4Switch(Switch):
    """Switch que arranca el binario simple_switch de BMv2."""

    def __init__(self, name, sw_path='simple_switch',
                 json_path='build/dns_cache.json',
                 thrift_port=9090, **kwargs):
        Switch.__init__(self, name, **kwargs)
        self.sw_path = sw_path
        self.json_path = json_path
        self.thrift_port = thrift_port

    def start(self, controllers):
        intf_args = []
        for intf in self.intfs.values():
            if intf.name != 'lo':
                intf_args.append('-i %d@%s' % (self.ports[intf], intf.name))
        intf_str = ' '.join(intf_args)

        cmd = '%s %s --thrift-port %d %s > /tmp/%s.log 2>&1 &' % (
            self.sw_path, intf_str, self.thrift_port, self.json_path, self.name)
        info('*** Iniciando switch %s: %s\n' % (self.name, cmd))
        os.system(cmd)
        time.sleep(1)

    def stop(self):
        os.system('pkill -f "thrift-port %d"' % self.thrift_port)


def main():
    setLogLevel('info')
    net = Mininet(controller=None)

    info('*** Creando switch P4\n')
    s1 = net.addSwitch('s1', cls=P4Switch)

    info('*** Creando hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')
    h5 = net.addHost('h5', ip='10.0.0.5/24', mac='00:00:00:00:00:05')  # servidor DNS

    info('*** Creando enlaces (en este orden -> puertos 1..5 del switch)\n')
    net.addLink(h1, s1)  # puerto 1
    net.addLink(h2, s1)  # puerto 2
    net.addLink(h3, s1)  # puerto 3
    net.addLink(h4, s1)  # puerto 4
    net.addLink(h5, s1)  # puerto 5

    net.start()
    info('*** Desactivando checksum offload en los hosts (necesario con BMv2)\n')
    for h in [h1, h2, h3, h4, h5]:
        h.cmd('ethtool -K %s-eth0 tx off rx off' % h.name)

    info('*** Configurando ARP estatico (el switch P4 no procesa ARP)\n')
    macs = {
        '10.0.0.1': '00:00:00:00:00:01',
        '10.0.0.2': '00:00:00:00:00:02',
        '10.0.0.3': '00:00:00:00:00:03',
        '10.0.0.4': '00:00:00:00:00:04',
        '10.0.0.5': '00:00:00:00:00:05',
    }
    for h in [h1, h2, h3, h4, h5]:
        for ip, mac in macs.items():
            if ip != h.IP():
                h.cmd('arp -s %s %s' % (ip, mac))

    info('*** Esperando a que simple_switch este listo\n')
    time.sleep(1)

    info('*** Cargando reglas de la tabla ipv4_lpm\n')
    os.system('simple_switch_CLI --thrift-port 9090 < commands.txt')

    info('\n*** Red lista.\n')
    info(' h1 h2 h3 h4 = clientes (10.0.0.1 - .4)\n')
    info(' h5 = servidor DNS (10.0.0.5)\n')
    info(' Probar con, por ejemplo: h1 python3 scripts/dns_client.py test1.com\n\n')

    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()
