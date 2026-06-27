#!/usr/bin/env python3
"""
Prueba de capacidad y colisiones de la cache DNS.

Genera N dominios distintos (host0000.test, host0001.test, ...), los
consulta una vez (poblando la cache: todas son MISS), y luego los vuelve
a consultar en el mismo orden para ver cuantos siguen siendo HIT y
cuantos volvieron a ser MISS.

La clasificacion hit/miss se hace comparando el tiempo de la 2da consulta
de un dominio contra el tiempo de SU propia 1ra consulta.

Uso (dentro del namespace de un host cliente, ej. h1):
    python3 scripts/capacity_test.py <N> [archivo_salida.csv]

Ejemplo:
    python3 scripts/capacity_test.py 1500 resultados_capacidad.csv
"""

import socket
import struct
import sys
import time
import csv

DNS_SERVER = '10.0.0.5'
DNS_PORT = 53
FMT = '!HBB32sII'

HIT_RATIO_THRESHOLD = 0.6


def pack_name(name):
    raw = name.encode('ascii')
    return raw[:32].ljust(32, b'\x00')


def query(sock, name, trans_id, timeout=2.0):
    sock.settimeout(timeout)
    packet = struct.pack(FMT, trans_id, 0x00, 1, pack_name(name), 0, 0)
    t0 = time.time()
    sock.sendto(packet, (DNS_SERVER, DNS_PORT))
    try:
        data, _ = sock.recvfrom(1024)
    except socket.timeout:
        return None, None
    elapsed_ms = (time.time() - t0) * 1000
    _, flags, _, raw_name, answer_ip, ttl = struct.unpack(FMT, data)
    ip_str = socket.inet_ntoa(struct.pack('!I', answer_ip))
    return elapsed_ms, ip_str


def main():
    if len(sys.argv) < 2:
        print('Uso: python3 scripts/capacity_test.py <N> [salida.csv]')
        sys.exit(1)

    n = int(sys.argv[1])
    csv_path = sys.argv[2] if len(sys.argv) > 2 else None

    domains = [f'host{i:04d}.test' for i in range(n)]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f'Fase 1: poblando la cache con {n} dominios distintos...')
    first_times = {}
    first_ips = {}
    for i, name in enumerate(domains):
        t, ip = query(sock, name, trans_id=i + 1)
        if t is None:
            print(f'  TIMEOUT en {name} (fase 1)')
            continue
        first_times[name] = t
        first_ips[name] = ip
        if (i + 1) % 200 == 0:
            print(f'  ...{i + 1}/{n} consultados')

    print(f'\nFase 2: re-consultando los mismos {n} dominios...')
    results = []
    hits = 0
    misses = 0
    wrong_ip = 0
    for i, name in enumerate(domains):
        if name not in first_times:
            continue
        t2, ip2 = query(sock, name, trans_id=10000 + i)
        if t2 is None:
            print(f'  TIMEOUT en {name} (fase 2)')
            continue

        is_hit = t2 < first_times[name] * HIT_RATIO_THRESHOLD
        correct = (ip2 == first_ips[name])
        if not correct:
            wrong_ip += 1
        if is_hit:
            hits += 1
        else:
            misses += 1

        results.append((name, first_times[name], t2, is_hit, correct))
        if (i + 1) % 200 == 0:
            print(f'  ...{i + 1}/{n} re-consultados')

    total = hits + misses
    print('\n' + '=' * 50)
    print(f' Resultados para N = {n} dominios (CACHE_SIZE = 1024)')
    print('=' * 50)
    print(f' Hits (2da consulta rapida) : {hits}')
    print(f' Misses/evictados : {misses}')
    print(f' Hit rate efectivo : {hits/total*100:.1f}%')
    print(f' Respuestas con IP INCORRECTA : {wrong_ip}  (deberia ser 0 siempre)')
    print('=' * 50)

    if csv_path:
        with open(csv_path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['dominio', 't1_ms', 't2_ms', 'hit', 'ip_correcta'])
            for row in results:
                w.writerow(row)
        print(f'Guardado en: {csv_path}')


if __name__ == '__main__':
    main()
