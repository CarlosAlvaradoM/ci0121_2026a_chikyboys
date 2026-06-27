#!/usr/bin/env python3
"""
Lee los contadores de hits/misses directamente de los registers del
switch P4 usando simple_switch_CLI, y muestra el hit rate.

Uso (desde Proyecto3/, fuera de Mininet, en la VM):
    python3 scripts/stats.py
"""

import subprocess


def read_register(reg_name, index=0, thrift_port=9090):
    cmd = f'echo "register_read {reg_name} {index}" | simple_switch_CLI --thrift-port {thrift_port}'
    out = subprocess.check_output(cmd, shell=True).decode()
    for line in out.splitlines():
        if reg_name in line and '=' in line:
            try:
                return int(line.strip().split('=')[-1].strip())
            except ValueError:
                continue
    return 0


def main():
    hits = read_register('reg_hits')
    misses = read_register('reg_misses')
    total = hits + misses
    rate = (hits / total * 100) if total else 0.0

    print('=' * 40)
    print(' Estadisticas de la cache DNS')
    print('=' * 40)
    print(f' Hits : {hits}')
    print(f' Misses : {misses}')
    print(f' Total : {total}')
    print(f' Hit rate : {rate:.1f}%')
    print('=' * 40)


if __name__ == '__main__':
    main()
