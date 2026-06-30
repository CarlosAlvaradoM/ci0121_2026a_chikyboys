from mininet.net import Mininet
from mininet.node import Switch
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import subprocess, os, time

class P4Switch(Switch):
    def __init__(self, name, json_path, thrift_port, **kwargs):
        kwargs['inNamespace'] = False
        Switch.__init__(self, name, **kwargs)
        self.json_path   = json_path
        self.thrift_port = thrift_port
        self.proc        = None

    def start(self, controllers):
        ifaces = []
        for i, intf in enumerate(self.intfList()):
            if intf.name != 'lo':
                ifaces += ['-i', f'{i}@{intf.name}']
        cmd = ['simple_switch',
               '--thrift-port', str(self.thrift_port),
               '--device-id',   str(self.thrift_port - 9089),
               '--log-console'] + ifaces + [self.json_path]
        log_file = open(f'/tmp/{self.name}.log', 'w')
        info(f'  Arrancando {self.name} (thrift:{self.thrift_port})\n')
        self.proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
        time.sleep(1)

    def stop(self):
        if self.proc:
            self.proc.terminate()

    def attach(self, intf): pass
    def detach(self, intf): pass


class CounterTopo(Topo):
    def build(self):
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'counters.json')
        s1 = self.addSwitch('s1', cls=P4Switch,
                             json_path=json_path, thrift_port=9090)
        for i in range(1, 5):
            self.addHost(f'h{i}', ip=f'10.0.0.{i}/24',
                        mac=f'00:00:00:00:00:0{i}')
        for i in range(1, 5):
            self.addLink(f'h{i}', s1)


def main():
    setLogLevel('info')
    net = Mininet(topo=CounterTopo(), controller=None)
    net.start()

    info('\n*** Configurando ARP estatico en los hosts...\n')
    s1_macs = {
        1: '00:00:00:01:01:01',
        2: '00:00:00:01:02:01',
        3: '00:00:00:01:03:01',
        4: '00:00:00:01:04:01',
    }

    for i in range(1, 5):
        host = net.get(f'h{i}')
        host.cmd('ip route del default 2>/dev/null')
        for j in range(1, 5):
            if j != i:
                host.cmd(f'arp -s 10.0.0.{j} {s1_macs[i]}')
        host.cmd('sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null')

    info('*** Red lista. Escribe "exit" para salir.\n')
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()
