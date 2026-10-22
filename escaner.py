import socket

host = "127.0.0.1"

print(f"Escaneando {host} (puertos 1-1024)...")

for port in range(1, 1025):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        if s.connect_ex((host, port)) == 0:
            print(f"Puerto {port}: ABIERTO")

print("Escaneo terminado.")
