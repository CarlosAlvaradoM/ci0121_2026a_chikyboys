from scapy.all import *
import random, sys, time

GATEWAY_MAC = '00:00:00:01:01:01'
DST_IPS     = ['10.0.0.2', '10.0.0.3', '10.0.0.4']

def main():
    if len(sys.argv) < 3:
        print("Uso: generate_traffic.py <iface> <src_ip>")
        sys.exit(1)

    iface  = sys.argv[1]
    src_ip = sys.argv[2]

    print(f"Generando trafico mixto desde {src_ip} via {iface}...")

    for i in range(20):
        dst = random.choice(DST_IPS)
        if dst == src_ip:
            continue

        eth = Ether(dst=GATEWAY_MAC)

        pkt_icmp = eth / IP(src=src_ip, dst=dst, proto=1) / ICMP()
        sendp(pkt_icmp, iface=iface, verbose=0)

        pkt_udp = eth / IP(src=src_ip, dst=dst, proto=17) / UDP(dport=5000) / Raw(b'X' * 100)
        sendp(pkt_udp, iface=iface, verbose=0)

        pkt_tcp = eth / IP(src=src_ip, dst=dst, proto=6) / TCP(dport=80, flags='S') / Raw(b'A' * 50)
        sendp(pkt_tcp, iface=iface, verbose=0)

        time.sleep(0.1)

    print(f"Trafico normal enviado desde {src_ip}.")

    print(f"Generando flujo elefante desde {src_ip} -> 10.0.0.2 ...")
    elephant_dst = '10.0.0.2' if src_ip != '10.0.0.2' else '10.0.0.3'
    for i in range(60):
        pkt = (Ether(dst=GATEWAY_MAC) /
               IP(src=src_ip, dst=elephant_dst, proto=6) /
               TCP(dport=443, flags='A') /
               Raw(b'E' * 1400))
        sendp(pkt, iface=iface, verbose=0)
        time.sleep(0.01)

    print(f"Flujo elefante completado desde {src_ip} -> {elephant_dst}.")

if __name__ == '__main__':
    main()
