from mininet.net import Mininet
from mininet.node import Switch
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.cli import CLI

import subprocess
import os
import time


class P4Switch(Switch):

    def __init__(self, name, json_path, thrift_port, **kwargs):
        kwargs['inNamespace'] = False
        super().__init__(name, **kwargs)

        self.json_path = json_path
        self.thrift_port = thrift_port
        self.proc = None

    def start(self, controllers):

        ifaces = []

        for i, intf in enumerate(self.intfList()):
            if intf.name != 'lo':
                ifaces.extend(['-i', f'{i}@{intf.name}'])

        cmd = [
            'simple_switch',
            '--thrift-port', str(self.thrift_port),
            '--device-id', str(self.thrift_port - 9089),
            '--log-console'
        ] + ifaces + [self.json_path]

        info(f'*** Arrancando {self.name} (thrift:{self.thrift_port})\n')

        log_file = open(f'/tmp/{self.name}.log', 'w')
        self.proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)

        time.sleep(1)

    def stop(self):
        if self.proc:
            self.proc.terminate()

    def attach(self, intf):
        pass

    def detach(self, intf):
        pass


class RouterTopo(Topo):

    def build(self):

        json_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'router.json'
        )

        s1 = self.addSwitch(
            's1',
            cls=P4Switch,
            json_path=json_path,
            thrift_port=9090
        )

        s2 = self.addSwitch(
            's2',
            cls=P4Switch,
            json_path=json_path,
            thrift_port=9091
        )

        s3 = self.addSwitch(
            's3',
            cls=P4Switch,
            json_path=json_path,
            thrift_port=9092
        )

        h1 = self.addHost(
            'h1',
            ip='10.0.1.1/24',
            mac='00:00:00:00:01:01',
            defaultRoute='via 10.0.1.254'
        )

        h2 = self.addHost(
            'h2',
            ip='10.0.2.1/24',
            mac='00:00:00:00:02:01',
            defaultRoute='via 10.0.2.254'
        )

        h3 = self.addHost(
            'h3',
            ip='10.0.3.1/24',
            mac='00:00:00:00:03:01',
            defaultRoute='via 10.0.3.254'
        )

        h4 = self.addHost(
            'h4',
            ip='10.0.4.1/24',
            mac='00:00:00:00:04:01',
            defaultRoute='via 10.0.4.254'
        )

        self.addLink(h1, s1)
        self.addLink(h2, s2)
        self.addLink(h3, s3)
        self.addLink(h4, s3)

        self.addLink(s1, s2)
        self.addLink(s2, s3)

def main():
    setLogLevel('info')
    net = Mininet(topo=RouterTopo(), controller=None)
    net.start()

    info('\n*** Configurando rutas y ARP estático en los hosts...\n')

    routers_mac = {
        'h1': '00:00:00:01:01:01',
        'h2': '00:00:00:02:02:01',
        'h3': '00:00:00:03:02:01',
        'h4': '00:00:00:03:03:01',
    }

    for hname, gw_mac in routers_mac.items():
        host = net.get(hname)
        intf = host.defaultIntf()
        host.cmd('ip route del default 2>/dev/null')
        host.cmd(f'ip route add 10.0.0.0/8 dev {intf}')

        for net_id in ['10.0.1.1', '10.0.2.1', '10.0.3.1', '10.0.4.1']:
            host.cmd(f'arp -s {net_id} {gw_mac}')

    info('*** Red lista. Escribe "exit" para salir.\n')
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
