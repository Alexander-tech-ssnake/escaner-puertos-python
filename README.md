# escaner-puertos-python
 
Escáner de puertos TCP escrito en Python con la librería estándar (`socket`), sin dependencias externas. Detecta puertos abiertos en un equipo, escanea en paralelo con hilos y lee el *banner* de los servicios para identificar qué software y qué versión están corriendo.
 
## Objetivo
 
- Entender cómo funciona por dentro una herramienta como nmap: handshake TCP, estados de un puerto y conexiones con sockets.
- Practicar Python aplicado a redes y seguridad: `socket`, `argparse`, hilos con `concurrent.futures` y validación de entradas.
- Documentar los problemas reales encontrados durante el desarrollo (falsos positivos y falsos negativos), no solo el código final.
## Requisitos
 
- Python 3.
- Linux o Windows con WSL (probado en Ubuntu sobre WSL).
- No requiere instalar ninguna librería: usa solo la biblioteca estándar.
## Instalación
 
```bash
git clone git@github.com:Alexander-tech-ssnake/escaner-puertos-python.git
cd escaner-puertos-python
```
 
## Uso
 
```bash
python3 escaner.py HOST [-p PUERTOS] [-t TIMEOUT] [-w HILOS]
```
 
| Opción | Descripción | Por defecto |
|---|---|---|
| `HOST` | IP o nombre del equipo a escanear | obligatorio |
| `-p`, `--puertos` | Puerto o rango, por ejemplo `22` o `1-1024` | `1-1024` |
| `-t`, `--timeout` | Segundos de espera por puerto | `2.0` |
| `-w`, `--hilos` | Hilos simultáneos | `50` |
 
Ejemplos:
 
```bash
python3 escaner.py 127.0.0.1                  # puertos 1-1024 de tu propio equipo
python3 escaner.py 127.0.0.1 -p 20-30         # solo el rango 20-30
python3 escaner.py localhost -p 22            # un único puerto
python3 escaner.py 127.0.0.1 -p 1-65535 -w 20 # todos los puertos, con 20 hilos
```
 
## Ejemplo de salida
 
Escaneo del servidor SSH de la propia máquina:
 
```
$ python3 escaner.py 127.0.0.1 -p 22
Escaneando 127.0.0.1 (127.0.0.1), puertos 22-22...
Puerto 22: ABIERTO  SSH-2.0-OpenSSH_10.2p1 Ubuntu-2ubuntu3.7
Escaneo terminado: 1 puerto(s) abierto(s).
```
 
Escaneo de un servidor web temporal (`python3 -m http.server 8000`):
 
```
$ python3 escaner.py 127.0.0.1 -p 8000
Escaneando 127.0.0.1 (127.0.0.1), puertos 8000-8000...
Puerto 8000: ABIERTO  HTTP/1.0 200 OK
Escaneo terminado: 1 puerto(s) abierto(s).
```
 
Si el host no se resuelve o el rango no es válido, el programa muestra un mensaje de error claro en lugar de un traceback.
 
## Cómo funciona
 
1. **Conexión TCP.** Para cada puerto se intenta una conexión con `socket.connect_ex()`. TCP establece una conexión con un *handshake* de tres pasos: el cliente envía SYN, el servidor responde SYN-ACK y el cliente confirma con ACK.
2. **Estados de un puerto.**
   - *Abierto:* el handshake se completa (`connect_ex` devuelve `0`).
   - *Cerrado:* el servidor responde con RST y la conexión es rechazada al instante (en Linux, código de error `111`).
   - *Filtrado:* no llega respuesta, normalmente porque un firewall descarta los paquetes, y el intento termina por timeout.
3. **Tipo de escaneo.** Es un *connect scan*: completa el handshake, por lo que es sencillo pero deja huella en el objetivo. Un escaneo SYN (como el de nmap por defecto) no lo completa y requiere paquetes manipulados a bajo nivel.
4. **Paralelismo.** `ThreadPoolExecutor` reparte los puertos entre varios hilos. Casi todo el tiempo de un escaneo es espera de red, por lo que los hilos permiten solapar esas esperas. `pool.map` devuelve los resultados en orden, así que la salida sale ordenada aunque los hilos terminen desordenados.
5. **Lectura de banners.** Cuando un puerto está abierto, el escáner intenta leer lo que el servicio envía al conectar (SSH se presenta solo). En los puertos HTTP comunes (80, 8000 y 8080) envía una petición `HEAD` porque el servidor no habla primero.
## Rendimiento
 
Tiempos medidos con 1 hilo frente a 100 hilos (con timeout de 1 s):
 
| Prueba | 1 hilo | 100 hilos |
|---|---|---|
| localhost, puertos 1-65535 | 3,2 s | 9,3 s |
| scanme.nmap.org, puertos 1-100 | 17,1 s | 1,6 s |
 
- En **localhost** los hilos empeoraron el tiempo: los puertos cerrados responden al instante, no hay espera que solapar, y el costo de gestionar los hilos domina.
- Contra un **host remoto** la mejora fue de unas 10 veces, porque ahí sí hay espera de red.
- Pero con 100 hilos y timeout de 1 s el escáner **no detectó el puerto 80**, que sí aparecía con 1 hilo (ver hallazgo 2). Por eso los valores por defecto son más conservadores: 50 hilos y 2 s.
## Hallazgos durante el desarrollo
 
**1. Un servicio puede estar enlazado a otra dirección.** `ss -tln` mostraba el puerto 53 en escucha, pero escanear `127.0.0.1` no lo reportaba. El servicio estaba enlazado a `127.0.0.53` y a otras direcciones, no a `127.0.0.1`. Un servicio solo responde en las direcciones donde escucha: `0.0.0.0` significa todas las interfaces (el SSH, accesible desde la red), mientras que `127.0.0.1` es solo local.
 
**2. Falso negativo por exceso de concurrencia.** Contra scanme.nmap.org, con 100 hilos y timeout de 1 s no apareció el puerto 80, que estaba abierto. Con tantas conexiones simultáneas alguna respuesta llegó fuera de tiempo, o la red limitó el ritmo. Un escáner más rápido que pierde puertos abiertos da una falsa sensación de seguridad; se corrigió con valores por defecto más prudentes.
 
**3. Falso positivo por autoconexión TCP.** Al escanear el rango dinámico de puertos (32768-60999) en `127.0.0.1`, aparecían puertos "abiertos" distintos en cada pasada (39408, 54140, 50800, 43098...) que `ss` no mostraba en escucha. Causa: al conectar a localhost, el sistema puede asignar al socket como puerto de origen el mismo número que el de destino, y el socket termina conectado consigo mismo. Solución: descartar los casos en que la dirección local y la remota del socket coinciden (`getsockname() == getpeername()`).
 
**4. Los escaneos dejan rastro.** El servidor web de prueba registró cada petición del escáner (`"HEAD / HTTP/1.0" 200`). Lo mismo ocurre con los intentos contra SSH: un analista puede detectar un escaneo revisando los logs, como se hace en el proyecto [analizador-logs-ssh](https://github.com/Alexander-tech-ssnake/analizador-logs-ssh).
 
**Sobre los banners:** el de SSH revela la versión exacta del software (`OpenSSH_10.2p1 Ubuntu-2ubuntu3.7`). Un atacante puede usarla para buscar vulnerabilidades conocidas de esa versión, por lo que mantener los servicios actualizados es la defensa principal.
 
## Limitaciones y mejoras futuras
 
### Limitaciones actuales
 
- Solo IPv4; no escanea direcciones IPv6.
- Solo TCP con *connect scan*: no hace escaneo SYN ni UDP.
- Solo lee banners útiles en servicios que hablan primero (como SSH) y en los puertos HTTP 80, 8000 y 8080.
- Sin reintentos: un puerto que no responde a tiempo se da por no abierto, lo que puede producir falsos negativos.
- No distingue entre puertos cerrados y filtrados; ambos se omiten de la salida.
- No exporta los resultados a un archivo.
### Mejoras futuras
 
- Mostrar el nombre del servicio de cada puerto (`socket.getservbyport`).
- Distinguir puertos cerrados de filtrados.
- Reintentar los puertos que agotan el tiempo de espera.
- Soporte para IPv6.
- Exportación de resultados a JSON o CSV.
- Escaneo SYN con Scapy.
## Aviso
 
Esta herramienta tiene fines educativos. Úsala solo en sistemas propios o con autorización explícita del propietario: escanear equipos ajenos sin permiso puede constituir una infracción legal. Para practicar fuera de tu equipo, el proyecto Nmap permite escaneos moderados de `scanme.nmap.org`.
