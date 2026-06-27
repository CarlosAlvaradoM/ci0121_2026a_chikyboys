# Cache DNS en el Data Plane (P4 / BMv2 / Mininet)

Proyecto - Etapa 3, Redes de Computadoras 2026.
Opcion A: Cache DNS.

## 1. Que hace este proyecto

Un switch P4 (BMv2) intercepta paquetes UDP/53. Si la consulta de un
dominio ya esta en la cache (guardada en *registers* dentro del propio
switch), responde inmediatamente sin tocar el servidor real. Si no esta,
deja pasar la consulta al servidor DNS real (simulado en Python) y, al
ver la respuesta pasar de vuelta, la guarda en la cache para la proxima
vez.

### Nota de diseno importante

El formato real de DNS (RFC 1035) tiene nombres de dominio de longitud
variable, lo cual es complejo de parsear en P4 sin loops acotados en el
parser. Para que el proyecto sea viable en el tiempo disponible, se
definio un formato **simplificado tipo DNS** de tamano fijo (ver
`dns_cache.p4`, header `dns_t`), generado por nuestros propios scripts en
Python (`scripts/dns_client.py` y `scripts/dns_server.py`). Esto es
valido porque el enunciado permite simular el servidor con Scapy/Python.
El parsing completo de RFC 1035 (nombres variable-length) se documenta en
el informe como limitacion conocida y trabajo futuro.

Formato usado (44 bytes total, dentro del payload UDP):

| Campo      | Tamano   | Descripcion                              |
|------------|----------|-------------------------------------------|
| trans_id   | 2 bytes  | identificador de transaccion              |
| flags      | 1 byte   | bit 0 = QR (0=consulta, 1=respuesta)      |
| qtype      | 1 byte   | 1 = registro tipo A                       |
| qname      | 32 bytes | dominio en ASCII, rellenado con 0x00      |
| answer_ip  | 4 bytes  | IP resuelta (0 en consultas)              |
| ttl        | 4 bytes  | segundos de validez                       |

## 2. Estructura de archivos

```
Proyecto3/
├── dns_cache.p4          # programa P4 (parser, registers, logica hit/miss)
├── topology.py           # script de Mininet (switch + 5 hosts)
├── commands.txt          # reglas de la tabla de reenvio (simple_switch_CLI)
├── Makefile              # compilar / correr / limpiar
├── README.md             # informacion del proyecto
├── test-graficas/        # resutados de test y las graficas
├── scripts/
│   ├── dns_server.py     # servidor DNS simulado (corre en h5)
│   ├── dns_client.py     # cliente de prueba (corre en h1..h4)
│   ├── capacity_test.py  # prueba de capacidad/colisiones de la cache
│   └── stats.py          # lee contadores de hits/misses del switch
└── build/                # (se genera al compilar) dns_cache.json
```

## 3. Instalación / dependencias

La VM que nos dio la profesora (p4-guide) ya trae instalado todo lo
necesario: `p4c`, `simple_switch`, `simple_switch_CLI`, Mininet y Python3.
No hay que instalar nada adicional. Solo asegurense de estar dentro del
entorno virtual que ya tiene activo:

```
(p4dev-python-venv) p4@p4dev:~/Desktop/Proyecto3$
```

Si por alguna razon ese venv no está activo, se activa con:

```bash
source ~/p4dev-python-venv/bin/activate
```

## 4. Paso a paso para correr el proyecto

### Paso 1 — Compilar el programa P4

```bash
cd ~/Desktop/Proyecto3
make
```

Esto corre `p4c --target bmv2 --arch v1model -o build dns_cache.p4`
y genera `build/dns_cache.json`.

### Paso 2 — Levantar la topología en Mininet

```bash
mn -c        # limpiar restos de una corrida anterior, por si quedaron
make run
```

Esto:
1. Crea el switch `s1` corriendo `simple_switch` con `dns_cache.json`.
2. Crea los hosts `h1`–`h5`.
3. Desactiva el *checksum offload* en cada host (necesario para que
   BMv2 reenvíe paquetes con checksums válidos, ver Sección 7).
4. Configura ARP estático en cada host (el switch P4 no procesa ARP).
5. Carga las reglas de reenvío desde `commands.txt` con `simple_switch_CLI`.
6. Te deja en la consola interactiva de Mininet: `mininet>`

### Paso 3 — Levantar el servidor DNS simulado (en h5)

```
mininet> xterm h5
```

Dentro:
```bash
cd ~/Desktop/Proyecto3
python3 scripts/dns_server.py
```

Dejar esa ventana abierta y corriendo durante todas las pruebas.

## 5. Pruebas realizadas

Todas las pruebas de esta sección se ejecutaron sobre la misma sesión de
Mininet (sin reiniciar el switch entre una y otra), con `dns_server.py`
corriendo en h5 durante toda la sesión.

### Test 1 — Latencia básica hit vs. miss, por dominio

En **h1** (`mininet> xterm h1`):

```bash
python3 scripts/dns_client.py test1.com 20 resultados_test1.csv
```

Repetido con los otros tres dominios:

```bash
python3 scripts/dns_client.py test2.com 20 resultados_test2.csv
python3 scripts/dns_client.py utn.ac.cr 20 resultados_utn.csv
python3 scripts/dns_client.py p4.org 20 resultados_p4org.csv
```

Cada corrida hace 1 consulta nueva (miss) + 19 repeticiones (hits) e
imprime un resumen de latencia promedio/mín/máx y % de reducción,
además de guardar cada medición individual en el `.csv` indicado.

**Resultado obtenido:** reducción de latencia entre 45.8% y 64.3% según
el dominio (promedio 53.4%). Ver Tabla de la Sección 4.2 del informe.

### Test 2 — Caché compartida entre todos los clientes

Con `test1.com` ya cacheado por el Test 1, se consultó por primera vez
desde cada uno de los otros tres hosts, que nunca lo habían pedido:

```
mininet> xterm h2 # dentro: python3 scripts/dns_client.py test1.com
mininet> xterm h3 # dentro: python3 scripts/dns_client.py test1.com
mininet> xterm h4 # dentro: python3 scripts/dns_client.py test1.com
```

**Resultado obtenido:** las tres consultas fueron resueltas como *hit*
(latencia baja, y sin que aparezca ninguna línea nueva en la consola de
`dns_server.py`), confirmando que la caché vive en el switch y es
compartida por todos los clientes, no por host.

### Test 3 — Hit rate acumulado (snapshot intermedio)

Desde una terminal **fuera** de Mininet:

```bash
python3 scripts/stats.py > stats_despues_tests_1_a_3.txt
```

**Resultado obtenido:** 82 hits, 4 misses, 86 consultas totales (95.3%
de hit rate) hasta ese punto de la sesión.

### Test 4 — Capacidad y colisiones de la caché

En **h1**, para cinco valores distintos de N (cantidad de dominios
distintos generados dinámicamente: `host0000.test`, `host0001.test`, ...):

```bash
python3 scripts/capacity_test.py 200 cap_200.csv
python3 scripts/capacity_test.py 800 cap_800.csv
python3 scripts/capacity_test.py 1024 cap_1024.csv
python3 scripts/capacity_test.py 1500 cap_1500.csv
python3 scripts/capacity_test.py 2000 cap_2000.csv
```

Cada corrida consulta los N dominios una vez (poblando la cache) y
los vuelve a consultar para medir cuántos siguen siendo *hit* y
cuántos fueron evictados por colisión de hash, verificando además que
ninguna respuesta tenga la IP de un dominio distinto al consultado.

**Resultado obtenido:** hit rate efectivo decreciente a medida que N se
acerca y supera `CACHE_SIZE = 1024` (86.0% en N=200, 11.7% en N=1024),
y **0 respuestas con IP incorrecta en todos los casos** — ver Sección
4.5 del informe para el análisis completo, incluyendo la discusión de
por qué la curva no es perfectamente monótona.

### Test 5 — Contador final y verificación de coherencia

```bash
python3 scripts/stats.py > stats_final.txt
```

**Resultado obtenido:** 4046 hits, 7088 misses, 11134 consultas totales
(36.3% de hit rate acumulado de toda la sesión). Este total coincide
exactamente con la suma esperada de consultas de todas las pruebas
anteriores (86 + 2×(200+800+1024+1500+2000) = 11134), lo cual valida
que los contadores del switch reflejan fielmente la actividad real.

### Generar las gráficas del informe

Con todos los `.csv` anteriores ya generados, desde la carpeta
`Proyecto3/`:

```bash
pip install matplotlib --break-system-packages
python3 generar_graficas.py
```

Esto produce `fig_latencia_hit_vs_miss.png`, `fig_capacidad_hitrate.png`
y `fig_dispersion_latencias.png`, usadas en `main.tex`.

### Salir

```
mininet> exit
make clean
mn -c
```

## 6. Declaración de uso de IA generativa

En cumplimiento del enunciado, se declara el alcance real
de la asistencia de IA (Claude, Anthropic) en este proyecto:

**Generado con asistencia de IA:**
- Guia y esqueleto de `dns_cache.p4` y de `topology.py`
- La estructura y plantilla del informe técnico (`main.tex`).
- Diagnóstico y resolución de dos bugs no triviales encontrados durante
  las pruebas: (1) una reescritura incorrecta de direcciones MAC en la
  acción `ipv4_forward` que corrompía los paquetes reenviados, detectada
  mediante análisis de capturas `tcpdump`; y (2) paquetes UDP descartados
  silenciosamente por *checksum offload* en las interfaces virtuales de
  Mininet, detectado mediante `netstat -su` (contador `InCsumErrors`) y
  resuelto desactivando el offload con `ethtool`.
