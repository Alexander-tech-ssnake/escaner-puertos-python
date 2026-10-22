import argparse
import socket
from concurrent.futures import ThreadPoolExecutor

def parsear_puertos(texto):
    """Convierte '1-1024' o '22' en una tupla (inicio, fin)."""
    if "-" in texto:
        inicio, fin = texto.split("-", 1)
    else:
        inicio = fin = texto
    inicio, fin = int(inicio), int(fin)
    if not (1 <= inicio <= fin <= 65535):
        raise argparse.ArgumentTypeError("rango inválido: usa valores entre 1 y 65535")
    return inicio, fin


def leer_banner(s, puerto):
    """Intenta leer el mensaje con el que se presenta el servicio."""
    try:
        if puerto in (80, 8000, 8080):
            # HTTP no habla primero: hay que pedirle algo
            s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
        datos = s.recv(1024)
    except OSError:
        return ""
    texto = datos.decode("utf-8", errors="replace").strip()
    return texto.splitlines()[0][:80] if texto else ""


def escanear_puerto(ip, puerto, timeout):
    """Devuelve (abierto, banner)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        if s.connect_ex((ip, puerto)) != 0:
            return False, ""
        if s.getsockname() == s.getpeername():
            return False, ""
        return True, leer_banner(s, puerto)


def main():
    parser = argparse.ArgumentParser(
        description="Escáner de puertos TCP (connect scan). "
                    "Úsalo solo en sistemas propios o con autorización."
    )
    parser.add_argument("host", help="IP o nombre del equipo a escanear")
    parser.add_argument("-p", "--puertos", type=parsear_puertos, default="1-1024",
                        help="puerto o rango, por ejemplo 22 o 1-1024 (por defecto 1-1024)")
    parser.add_argument("-t", "--timeout", type=float, default=2.0,
                        help="segundos de espera por puerto (por defecto 2.0)")
    parser.add_argument("-w", "--hilos", type=int, default=50,
			help="hilos simultáneos (por defecto 50)")
    args = parser.parse_args()

    try:
        ip = socket.gethostbyname(args.host)
    except socket.gaierror:
        parser.error(f"no se pudo resolver el host '{args.host}'")

    inicio, fin = args.puertos
    print(f"Escaneando {args.host} ({ip}), puertos {inicio}-{fin}...")

    if args.hilos < 1:
        parser.error("--hilos debe ser al menos 1")

    abiertos = 0
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        resultados = pool.map(
            lambda p: (p, *escanear_puerto(ip, p, args.timeout)),
            range(inicio, fin + 1),
        )
        for puerto, abierto, banner in resultados:
            if abierto:
                extra = f"  {banner}" if banner else ""
                print(f"Puerto {puerto}: ABIERTO{extra}")
                abiertos += 1

    print(f"Escaneo terminado: {abiertos} puerto(s) abierto(s).")


if __name__ == "__main__":
    main()
