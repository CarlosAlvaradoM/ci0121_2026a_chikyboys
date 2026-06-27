#!/usr/bin/env python3
"""
Cliente DNS de prueba (corre en h1, h2, h3 o h4).

Envia una consulta con nuestro formato simplificado tipo DNS al servidor
(10.0.0.5), mide el tiempo de respuesta y muestra el resultado.

Uso (dentro del namespace de un host cliente):
    python3 scripts/dns_client.py <dominio> [repeticiones]

Ejemplos:
    python3 scripts/dns_client.py test1.com
    python3 scripts/dns_client.py test1.com 5
"""

import socket
import struct
import sys
import time

DNS_SERVER = '10.0.0.5'
DNS_PORT = 53
FMT = '!HBB32sII'  # debe coincidir con dns_cache.p4 y dns_server.py


def pack_name(name):
    raw = name.encode('ascii')
    return raw[:32].ljust(32, b'\x00')


def query(name, trans_id=1, timeout=2.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    packet = struct.pack(FMT, trans_id, 0x00, 1, pack_name(name), 0, 0)

    t0 = time.time()
    sock.sendto(packet, (DNS_SERVER, DNS_PORT))
    try:
        data, _ = sock.recvfrom(1024)
    except socket.timeout:
        print(f'  -> TIMEOUT consultando {name}')
        return None
    elapsed_ms = (time.time() - t0) * 1000

    _, flags, _, raw_name, answer_ip, ttl = struct.unpack(FMT, data)
    ip_str = socket.inet_ntoa(struct.pack('!I', answer_ip))
    qname = raw_name.rstrip(b'\x00').decode('ascii')

    print(f'  {qname} -> {ip_str}  (ttl={ttl}s)  [{elapsed_ms:.3f} ms]')
    return elapsed_ms


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'test1.com'
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    csv_path = sys.argv[3] if len(sys.argv) > 3 else None

    print(f'Consultando "{name}" {reps} vez(es)...')
    times = []
    for i in range(reps):
        t = query(name, trans_id=i + 1)
        if t is not None:
            times.append(t)

    if reps > 1 and len(times) > 1:
        first = times[0]
        rest = times[1:]
        avg_rest = sum(rest) / len(rest)
        print()
        print(f' 1ra consulta (probable MISS) : {first:.3f} ms')
        print(f' Resto ({len(rest)} consultas, probable HIT):')
        print(f' promedio : {avg_rest:.3f} ms')
        print(f' minimo : {min(rest):.3f} ms')
        print(f' maximo : {max(rest):.3f} ms')
        if avg_rest > 0:
            print(f'  Reduccion de latencia: {(1 - avg_rest/first)*100:.1f}%')

    if csv_path:
        import csv
        with open(csv_path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['intento', 'dominio', 'latencia_ms'])
            for i, t in enumerate(times):
                w.writerow([i + 1, name, f'{t:.3f}'])
        print(f'\n  Guardado en: {csv_path}')


if __name__ == '__main__':
    main()
