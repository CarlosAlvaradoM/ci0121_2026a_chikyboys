#!/usr/bin/env python3
"""
Genera las graficas para el informe a partir de los .csv producidos

Uso:
    pip install matplotlib --break-system-packages
    python3 generar_graficas.py

Genera 3 archivos .png en escala de grises:
    fig_latencia_hit_vs_miss.png
    fig_capacidad_hitrate.png
    fig_dispersion_latencias.png
"""

import csv
import statistics as st
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.size': 11,
    'axes.edgecolor': 'black',
    'axes.labelcolor': 'black',
    'text.color': 'black',
})

LATENCY_FILES = {
    'test1.com': 'resultados_test1.csv',
    'test2.com': 'resultados_test2.csv',
    'utn.ac.cr': 'resultados_utn.csv',
    'p4.org': 'resultados_p4org.csv',
}

CAPACITY_FILES = {
    200: 'cap_200.csv',
    800: 'cap_800.csv',
    1024: 'cap_1024.csv',
    1500: 'cap_1500.csv',
    2000: 'cap_2000.csv',
}

CACHE_SIZE = 1024


def read_latency_csv(path):
    times = []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            times.append(float(row['latencia_ms']))
    return times


def grafico_latencia():
    dominios = list(LATENCY_FILES.keys())
    miss_vals, hit_avg_vals, hit_std_vals = [], [], []

    for dom, path in LATENCY_FILES.items():
        times = read_latency_csv(path)
        miss_vals.append(times[0])
        hits = times[1:]
        hit_avg_vals.append(st.mean(hits))
        hit_std_vals.append(st.stdev(hits) if len(hits) > 1 else 0)

    x = list(range(len(dominios)))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar([i - width / 2 for i in x], miss_vals, width, label='Miss (1ra consulta)', color='0.85', edgecolor='black', hatch='//')
    ax.bar([i + width / 2 for i in x], hit_avg_vals, width, yerr=hit_std_vals, capsize=4, label='Hit (promedio de 19 repeticiones)', color='0.4', edgecolor='black')

    ax.set_ylabel('Latencia (ms)')
    ax.set_xlabel('Dominio consultado')
    ax.set_title('Latencia: consulta MISS vs. HIT por dominio')
    ax.set_xticks(x)
    ax.set_xticklabels(dominios)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig('fig_latencia_hit_vs_miss.png', dpi=200)
    plt.close(fig)
    print('Generado: fig_latencia_hit_vs_miss.png')


def grafico_capacidad():
    ns, hit_rates = [], []
    for n, path in sorted(CAPACITY_FILES.items()):
        hits = total = 0
        with open(path, newline='') as f:
            for row in csv.DictReader(f):
                total += 1
                if row['hit'].strip().lower() == 'true':
                    hits += 1
        ns.append(n)
        hit_rates.append(hits / total * 100 if total else 0)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(ns, hit_rates, marker='o', color='black', linewidth=1.5, markerfacecolor='white', markersize=7, label='Hit rate efectivo')
    ax.axvline(CACHE_SIZE, color='black', linestyle='--', linewidth=1, label=f'CACHE_SIZE = {CACHE_SIZE}')
    ax.set_xlabel('Cantidad de dominios distintos consultados (N)')
    ax.set_ylabel('Hit rate efectivo (%)')
    ax.set_title('Hit rate efectivo vs. cantidad de dominios (capacidad de la cache)')
    ax.set_ylim(0, 100)
    ax.grid(linestyle='--', alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig('fig_capacidad_hitrate.png', dpi=200)
    plt.close(fig)
    print('Generado: fig_capacidad_hitrate.png')


def grafico_dispersion():
    path = CAPACITY_FILES[200]
    t1_hit, t2_hit, t1_miss, t2_miss = [], [], [], []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            t1 = float(row['t1_ms'])
            t2 = float(row['t2_ms'])
            if row['hit'].strip().lower() == 'true':
                t1_hit.append(t1)
                t2_hit.append(t2)
            else:
                t1_miss.append(t1)
                t2_miss.append(t2)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(t1_hit, t2_hit, marker='o', facecolors='none', edgecolors='black', label='Clasificado HIT', s=35)
    ax.scatter(t1_miss, t2_miss, marker='x', color='black', label='Clasificado MISS/evictado', s=35)
    todos = t1_hit + t1_miss + t2_hit + t2_miss
    lims = [0, max(todos) * 1.05] if todos else [0, 1]
    ax.plot(lims, lims, color='0.6', linestyle=':', linewidth=1, label='t2 = t1')
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel('Latencia 1ra consulta (ms)')
    ax.set_ylabel('Latencia 2da consulta (ms)')
    ax.set_title('Dispersion de latencias, N=200 (prueba de capacidad)')
    ax.grid(linestyle='--', alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig('fig_dispersion_latencias.png', dpi=200)
    plt.close(fig)
    print('Generado: fig_dispersion_latencias.png')


def main():
    grafico_latencia()
    grafico_capacidad()
    grafico_dispersion()


if __name__ == '__main__':
    main()
