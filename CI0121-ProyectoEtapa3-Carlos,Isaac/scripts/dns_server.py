#!/usr/bin/env python3
"""
Servidor DNS simulado (corre en h5, 10.0.0.5).

Escucha en UDP/53 paquetes con nuestro formato simplificado tipo DNS,
busca el dominio en un diccionario fijo de registros y responde con
QR=1 y la IP correspondiente.

Uso (dentro del namespace de h5):
    python3 scripts/dns_server.py
"""

import socket
import struct
import hashlib

DNS_PORT = 53
TTL = 30

# Formato de la cabecera "tipo DNS"
FMT = '!HBB32sII'

RECORDS = {
    'test1.com': '20.0.0.1',
    'test2.com': '20.0.0.2',
    'utn.ac.cr': '20.0.0.3',
    'p4.org': '20.0.0.4',
}


def generate_ip(name):
    """IP determinística para cualquier dominio no listado en records"""
    h = hashlib.md5(name.encode('ascii')).digest()
    return f'30.0.{h[0]}.{h[1]}'


def pack_name(name):
    raw = name.encode('ascii')
    return raw[:32].ljust(32, b'\x00')


def unpack_name(raw):
    return raw.rstrip(b'\x00').decode('ascii')


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', DNS_PORT))
    print(f'[dns_server] escuchando en UDP/{DNS_PORT} ...')
    print(f'[dns_server] registros disponibles: {list(RECORDS.keys())}')

    while True:
        data, addr = sock.recvfrom(1024)
        if len(data) != struct.calcsize(FMT):
            print(f'[dns_server] paquete de tamano inesperado de {addr}, se ignora')
            continue

        trans_id, flags, qtype, raw_name, answer_ip, ttl = struct.unpack(FMT, data)
        qr = flags & 0x1
        if qr != 0:
            continue  # no es una consulta, se ignora

        name = unpack_name(raw_name)
        ip_str = RECORDS.get(name) or generate_ip(name)
        ip_packed = struct.unpack('!I', socket.inet_aton(ip_str))[0]

        response = struct.pack(FMT, trans_id, flags | 0x1, qtype, pack_name(name), ip_packed, TTL)
        sock.sendto(response, addr)
        print(f'[dns_server] consulta de {addr}: {name} -> {ip_str}')


if __name__ == '__main__':
    main()
