# Redes Programables con P4 — Laboratorios

Implementación de dos sistemas en P4 sobre BMv2/Mininet: un router IPv4 estático (Lab 1) y un sistema de monitoreo de tráfico con contadores y detección de flujos elefante (Lab 2).

## Tabla de contenidos

- [Requisitos previos](#requisitos-previos)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Conceptos clave antes de empezar](#conceptos-clave-antes-de-empezar)
- [Lab 1 — Router IPv4 Estático](#lab-1--router-ipv4-estático)
- [Lab 2 — Contadores y Estadísticas de Tráfico](#lab-2--contadores-y-estadísticas-de-tráfico)
- [Errores comunes y soluciones](#errores-comunes-y-soluciones)
- [Limpieza al terminar](#limpieza-al-terminar)

---

## Requisitos previos

Esta guía asume la VM de p4-guide (Ubuntu 24.04) con el entorno P4 ya instalado: `p4c`, `BMv2` (`simple_switch`, `simple_switch_CLI`), `Mininet` y `Scapy` (este último vive dentro de un virtualenv, ver más abajo).

Al abrir una terminal nueva, activa siempre el entorno:

```bash
source ~/p4setup.bash
```

Localiza la ruta de tu virtualenv con Scapy (la necesitarás constantemente para los scripts de prueba):

```bash
which python3                              # python del sistema (sin Scapy)
python3 -c "import scapy" 2>&1             # confirma si scapy NO está aquí
find / -name "scapy" -path "*site-packages*" 2>/dev/null   # localiza el venv real
```

En esta guía se asume que el Python con Scapy está en:
```
/home/p4/src/p4dev-python-venv/bin/python3
```//
Ajusta esa ruta en todos los comandos si en tu VM es distinta.

---

## Estructura del repositorio

```
proyecto-p4/
├── README.md
├── lab1-router/
│   ├── router.p4              # Programa P4 del router
│   ├── router.json            # Compilado (generado por p4c)
│   ├── topology.py            # Topología Mininet: 3 routers + 4 hosts
│   └── configure_router.py    # Inserta las rutas LPM en cada router
├── lab2-counters/
│   ├── counters.p4            # Programa P4 de monitoreo
│   ├── counters.json          # Compilado (generado por p4c)
│   ├── topology.py            # Topología Mininet: 1 switch + 4 hosts
│   ├── install_flows.py       # Pre-instala entradas de flujo (activa direct counters)
│   ├── generate_traffic.py    # Genera tráfico TCP/UDP/ICMP + flujo elefante
│   └── controller.py          # Lee y muestra contadores cada 5 segundos
└── informe/
    └── informe.pdf
```

---

## Conceptos clave antes de empezar

Estos puntos evitan el 90% de los problemas que surgen al ejecutar estos labs:

**1. La red de Mininet vive en una sola terminal.** Todo (tablas, procesos `simple_switch`, estado del switch) muere si cierras el CLI de Mininet (`exit`) o corres `sudo mn -c`. El flujo correcto siempre es: levantar la topología en una terminal y dejarla abierta, configurar/probar desde una segunda terminal.

**2. El orden de los comandos `addLink()` en `topology.py` determina los números de puerto reales del switch**, no necesariamente el orden en que tú los piensas. Antes de configurar cualquier tabla, siempre verifica el mapeo real con:
```bash
mininet> links
```

**3. Scapy no está en el Python del sistema.** Todos los scripts de prueba con Scapy deben ejecutarse con la ruta completa al Python del virtualenv, nunca con `python3` a secas dentro de Mininet.

**4. Los hosts de Mininet no tienen gateway real.** No uses `defaultRoute` al crear hosts; en su lugar, se configuran rutas estáticas y entradas ARP estáticas manualmente (ya está resuelto en los `topology.py` de este repo).

**5. Cada vez que relanzas `topology.py`, todo el estado del switch se reinicia** (tablas vacías, registers en 0). Siempre hay que volver a correr los scripts de configuración después de levantar la topología.

---

## Lab 1 — Router IPv4 Estático

### Qué hace

Un router IPv4 con tabla de enrutamiento LPM (Longest Prefix Match) configurada estáticamente, que decrementa el TTL en cada salto, descarta paquetes con TTL agotado, reescribe direcciones MAC origen/destino, y descarta por defecto el tráfico sin ruta conocida.

### Topología

3 routers P4 (s1, s2, s3) interconectados, 4 hosts en subredes distintas:

```
h1 (10.0.1.1/24) --- s1 --- s2 --- s3 --- h3 (10.0.3.1/24)
                                    |
                                   h4 (10.0.4.1/24)
h2 (10.0.2.1/24) -------- s2
```

### Paso 1 — Compilar

```bash
cd ~/proyecto-p4/lab1-router
p4c --target bmv2 --arch v1model router.p4
```

Esto genera `router.json`. Si hay errores de sintaxis, revisa la versión de `p4c` instalada con `p4c --version`.

### Paso 2 — Levantar la topología (Terminal A)

```bash
sudo pkill -9 simple_switch 2>/dev/null
sudo mn -c
sudo python3 topology.py
```

Espera a ver el prompt `mininet>` y **deja esta terminal abierta**. No la cierres en ningún momento mientras trabajas.

### Paso 3 — Verificar la topología real

```bash
mininet> links
```

Resultado esperado:
```
h1-eth0<->s1-eth1
h2-eth0<->s2-eth1
h3-eth0<->s3-eth1
h4-eth0<->s3-eth2
s1-eth2<->s2-eth2
s2-eth3<->s3-eth3
```

Si tu salida es distinta, los números de puerto en `configure_router.py` deben ajustarse para que coincidan.

### Paso 4 — Configurar las tablas LPM (Terminal B)

```bash
cd ~/proyecto-p4/lab1-router
python3 configure_router.py
```

Debe terminar sin mensajes de "Could not connect". Verifica las tablas:

```bash
simple_switch_CLI --thrift-port 9090 <<< "table_dump ipv4_lpm"
simple_switch_CLI --thrift-port 9091 <<< "table_dump ipv4_lpm"
simple_switch_CLI --thrift-port 9092 <<< "table_dump ipv4_lpm"
```

Cada switch debe mostrar 4 entradas LPM (una por subred) más la entrada por defecto (`drop`).

### Paso 5 — Probar conectividad (Terminal A)

```bash
mininet> h1 ping -c3 h4
mininet> h2 ping -c3 h3
mininet> h1 ping -c3 h2
```

Resultado esperado: 0% packet loss en todos los casos, con TTL decreciente según el número de saltos (por ejemplo, h1→h4 atraviesa 3 routers, así que el TTL recibido será 3 menos que el enviado).

### Paso 6 — Verificar decremento de TTL con Scapy

```bash
mininet> h1 /home/p4/src/p4dev-python-venv/bin/python3 -c "
from scapy.all import *
pkt = IP(dst='10.0.4.1', ttl=64)/ICMP()
ans = sr1(pkt, iface='h1-eth0', timeout=2)
print('TTL enviado: 64')
print('TTL recibido:', ans[IP].ttl if ans else 'sin respuesta')
"
```

Resultado esperado: `TTL recibido: 61` (64 − 3 saltos).

### Paso 7 — Verificar descarte por TTL agotado

```bash
mininet> xterm s3
```

Dentro de la ventana xterm:
```bash
tcpdump -i s3-eth2 -n -e
```

De vuelta en la terminal principal de Mininet:
```bash
mininet> h1 /home/p4/src/p4dev-python-venv/bin/python3 -c "
from scapy.all import *
pkt = Ether(dst='00:00:00:01:01:01')/IP(src='10.0.1.1', dst='10.0.4.1', ttl=3)/ICMP()
sendp(pkt, iface='h1-eth0')
print('Enviado con TTL=3')
"
```

Resultado esperado: nada aparece en la ventana xterm (el paquete se descartó en s3, el tercer salto, antes de llegar a h4).

### Paso 8 — Verificar descarte por falta de ruta

```bash
mininet> s1 tcpdump -i s1-eth1 -n -w /tmp/s1-in.pcap -c 2 &
mininet> s1 tcpdump -i s1-eth2 -n -w /tmp/s1-out.pcap -c 2 &
mininet> h1 /home/p4/src/p4dev-python-venv/bin/python3 -c "
from scapy.all import *
pkt = Ether(dst='00:00:00:01:01:01')/IP(src='10.0.1.1', dst='8.8.8.8', ttl=64)/ICMP()
sendp(pkt, iface='h1-eth0')
"
mininet> s1 tcpdump -n -r /tmp/s1-in.pcap
mininet> s1 tcpdump -n -r /tmp/s1-out.pcap
```

Resultado esperado: el paquete aparece en `s1-in.pcap` (entró al router) pero **no** en `s1-out.pcap` (nunca se reenvió, porque `8.8.8.8` no tiene ruta en la tabla LPM y se activó el `default_action = drop()`).

---

## Lab 2 — Contadores y Estadísticas de Tráfico

### Qué hace

Un sistema de monitoreo en el plano de datos P4 que cuenta tráfico por protocolo (TCP/UDP/ICMP/otros), mantiene contadores directos por flujo (IP origen + IP destino), acumula bytes por flujo en un register, y marca como "elefante" cualquier flujo que supere un umbral configurable. Un controlador en Python lee y muestra todo esto cada 5 segundos.

### Topología

1 switch P4 (s1) con 4 hosts conectados directamente:

```
h1 (10.0.0.1) ---\
h2 (10.0.0.2) -----> s1
h3 (10.0.0.3) -----/
h4 (10.0.0.4) ---/
```

El switch reenvía todo el tráfico de forma fija por el puerto 2 (hacia h2); esto es intencional, ya que el propósito de este laboratorio es medir tráfico, no enrutarlo. **No uses `ping` normal para probar este lab**, usa los scripts con Scapy descritos abajo.

### Paso 1 — Compilar

```bash
cd ~/proyecto-p4/lab2-counters
p4c --target bmv2 --arch v1model counters.p4
```

### Paso 2 — Levantar la topología (Terminal A)

```bash
sudo pkill -9 simple_switch 2>/dev/null
sudo mn -c
sudo python3 topology.py
```

Deja esta terminal abierta con el `mininet>` activo.

```bash
mininet> links
```

Resultado esperado:
```
h1-eth0<->s1-eth1
h2-eth0<->s1-eth2
h3-eth0<->s1-eth3
h4-eth0<->s1-eth4
```

### Paso 3 — Configurar el umbral de flujo elefante (Terminal B)

Los registers de BMv2 se reinician a 0 cada vez que se relanza la topología, así que hay que fijar el umbral manualmente en cada arranque:

```bash
cd ~/proyecto-p4/lab2-counters
simple_switch_CLI --thrift-port 9090 <<< "register_write elephant_threshold 0 5000"
```

Verifica:
```bash
simple_switch_CLI --thrift-port 9090 <<< "register_read elephant_threshold 0"
```

Resultado esperado: `elephant_threshold[0]= 5000`.

### Paso 4 — Pre-instalar las entradas de flujo

Esto activa los direct counters reales para cada combinación posible de hosts:

```bash
python3 install_flows.py
```

Verifica que se hayan instalado 12 entradas (4 hosts × 3 destinos posibles cada uno):

```bash
simple_switch_CLI --thrift-port 9090 <<< "table_dump flow_stats" | grep -c "Dumping entry"
```

Resultado esperado: `12`.

### Paso 5 — Arrancar el controlador

En la misma Terminal B (o una tercera, según prefieras):

```bash
python3 controller.py
```

Déjalo corriendo. El primer ciclo mostrará todos los contadores en cero, ya que aún no se ha generado tráfico.

### Paso 6 — Generar tráfico mixto desde los 4 hosts (Terminal A)

```bash
mininet> h1 /home/p4/src/p4dev-python-venv/bin/python3 generate_traffic.py h1-eth0 10.0.0.1
mininet> h2 /home/p4/src/p4dev-python-venv/bin/python3 generate_traffic.py h2-eth0 10.0.0.2
mininet> h3 /home/p4/src/p4dev-python-venv/bin/python3 generate_traffic.py h3-eth0 10.0.0.3
mininet> h4 /home/p4/src/p4dev-python-venv/bin/python3 generate_traffic.py h4-eth0 10.0.0.4
```

Cada ejecución genera tráfico TCP, UDP e ICMP normal entre hosts aleatorios, además de un flujo grande ("elefante") dirigido a un destino fijo.

### Paso 7 — Verificar resultados

Observa la salida del `controller.py` (Terminal B). Cada 5 segundos debe mostrar algo similar a:

```
----------------------------------------------------------
  00:24:30
----------------------------------------------------------
  Protocolo    Paquetes       Bytes
  TCP              160       178,640
  UDP               40         5,680
  ICMP              45         2,170
  otros              0             0

  Flujos activos (3 de 12 posibles):
  10.0.0.1 -> 10.0.0.2     pkts=   81  bytes=   89,256 *** ELEFANTE ***
  10.0.0.1 -> 10.0.0.3     pkts=   18  bytes=    1,728
  10.0.0.1 -> 10.0.0.4     pkts=   21  bytes=    2,016
```

Confirma que: (1) los contadores por protocolo reflejan tráfico real, (2) los flujos activos muestran paquetes y bytes coherentes con lo generado, y (3) el flujo con mayor volumen está marcado como `*** ELEFANTE ***`.

### Paso 8 (opcional) — Inspeccionar el register de bytes directamente

```bash
simple_switch_CLI --thrift-port 9090 <<< "register_read flow_byte_count"
```

Muestra el contenido crudo del register indexado por hash de flujo (útil para depuración o para el video demostrativo).

---

## Errores comunes y soluciones

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'p4_mininet'` | El módulo de los tutoriales oficiales no está en el path, o la versión copiada es incompatible | Usa el `topology.py` de este repo, que define su propia clase `P4Switch` sin depender de `p4_mininet` |
| `Could not connect to thrift client on port 90XX` | La topología no está corriendo, o se cerró el CLI de Mininet | Vuelve a levantar `topology.py` y, sin cerrarlo, corre el script de configuración en otra terminal |
| `ping: Destination Host Unreachable` | El host no tiene ruta hacia el destino | Revisa `ip route` en el host; no debe haber `defaultRoute` apuntando a un gateway inexistente |
| `ping: Network is unreachable` | El destino no cae en ninguna ruta conocida por el kernel del host | Esperado si pruebas IPs fuera de las subredes configuradas (ej. `8.8.8.8`); usa Scapy con `sendp()` para inyectar el frame directamente |
| 100% packet loss aunque las tablas estén bien | Los puertos asumidos en el script de configuración no coinciden con los reales | Corre `mininet> links` y ajusta los números de puerto según el cableado real |
| `Invalid table operation (DUPLICATE_ENTRY)` | Las tablas ya estaban configuradas de una ejecución anterior sobre la misma instancia viva | No es un error real; verifica con `table_dump` que las entradas siguen correctas. Si quieres reconfigurar desde cero, usa `table_clear` primero |
| `tcpdump: Permission denied` al leer un .pcap | El archivo fue creado por un proceso con otro usuario/permisos | Usa `sudo tcpdump -r archivo.pcap`, o evita escribir a archivo y captura directo en consola con `-c N` |
| `ModuleNotFoundError: No module named 'scapy'` dentro de Mininet | Scapy solo está instalado en un virtualenv, no en el Python del sistema | Usa la ruta completa al Python del venv: `/home/p4/src/p4dev-python-venv/bin/python3` |
| El register de flujo elefante marca todo como elefante de inmediato | El umbral nunca se configuró tras el último arranque (los registers inician en 0) | Corre `register_write elephant_threshold 0 <valor>` después de cada `topology.py` |
| El controlador del Lab 2 muestra "(sin trafico aun)" tras generar tráfico | `install_flows.py` no se ejecutó, o las IPs usadas en `generate_traffic.py` no coinciden con las pre-instaladas | Verifica `table_dump flow_stats` y confirma que tiene 12 entradas antes de generar tráfico |

---

## Limpieza al terminar

Al finalizar las pruebas de cualquiera de los dos labs:

```bash
mininet> exit
```

```bash
sudo mn -c
sudo pkill -9 simple_switch 2>/dev/null
```

Esto detiene la red virtual, libera las interfaces de red y mata cualquier proceso `simple_switch` que haya quedado huérfano.
