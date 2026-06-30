import subprocess
import time
import re
import socket
import struct

THRIFT_PORT = 9090
INTERVAL    = 5
ELEPHANT_THRESHOLD = 5000

PROTO_NAMES = {0: 'TCP', 1: 'UDP', 2: 'ICMP', 3: 'otros'}

HOSTS = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4']

FLOW_HANDLES = []
h = 0
for src in HOSTS:
    for dst in HOSTS:
        if src != dst:
            FLOW_HANDLES.append((h, src, dst))
            h += 1


def cli(cmd: str) -> str:
    p = subprocess.Popen(
        ['simple_switch_CLI', '--thrift-port', str(THRIFT_PORT)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, _ = p.communicate(cmd.encode())
    return out.decode()


def read_proto_counters():
    output = cli(
        "counter_read proto_counter 0\n"
        "counter_read proto_counter 1\n"
        "counter_read proto_counter 2\n"
        "counter_read proto_counter 3\n"
    )
    results = {}
    for idx, m in enumerate(re.finditer(
            r'proto_counter\[\d+\]=\s*\((\d+)\s*bytes,\s*(\d+)\s*packets\)', output)):
        bts, pkts = int(m.group(1)), int(m.group(2))
        results[idx] = (pkts, bts)
    return results


def read_flow_counters():
    cmd = "".join(f"counter_read flow_counter {h}\n" for h, _, _ in FLOW_HANDLES)
    output = cli(cmd)

    flows = []
    matches = re.findall(
        r'flow_counter\[(\d+)\]=\s*\((\d+)\s*bytes,\s*(\d+)\s*packets\)', output)
    counter_by_handle = {int(h): (int(bts), int(pkts)) for h, bts, pkts in matches}

    for handle, src, dst in FLOW_HANDLES:
        bts, pkts = counter_by_handle.get(handle, (0, 0))
        flows.append((src, dst, pkts, bts))
    return flows


def main():
    print("=== Controlador de Monitoreo de Trafico P4 (Lab 2) ===")
    print(f"Umbral de flujo elefante: {ELEPHANT_THRESHOLD:,} bytes")
    print("Leyendo cada {} segundos. Ctrl+C para salir.\n".format(INTERVAL))

    try:
        while True:
            ts = time.strftime('%H:%M:%S')
            print(f"\n{'-'*58}")
            print(f"  {ts}")
            print(f"{'-'*58}")

            proto = read_proto_counters()
            print("  Protocolo    Paquetes       Bytes")
            for idx, name in PROTO_NAMES.items():
                pkts, bts = proto.get(idx, (0, 0))
                print(f"  {name:<10}  {pkts:>8}    {bts:>10,}")

            flows = read_flow_counters()
            active = [f for f in flows if f[2] > 0]
            print(f"\n  Flujos activos ({len(active)} de {len(flows)} posibles):")
            if not active:
                print("  (sin trafico aun)")
            for src, dst, pkts, bts in active:
                tag = " *** ELEFANTE ***" if bts > ELEPHANT_THRESHOLD else ""
                print(f"  {src} -> {dst:<12} pkts={pkts:>5}  bytes={bts:>9,}{tag}")

            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\nControlador detenido.")


if __name__ == '__main__':
    main()
