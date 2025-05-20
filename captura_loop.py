import time
from datetime import datetime
from capturar_imagenes import capturar_y_guardar

INTERVALO_MINUTOS = 60

def main():
    print("Iniciando loop de captura de imágenes.")
    try:
        while True:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Capturando imagen...")
            try:
                capturar_y_guardar()
            except Exception as e:
                print(f"[ERROR] Falló la captura: {e}")

            print(f"Esperando {INTERVALO_MINUTOS} minutos...\n")
            time.sleep(INTERVALO_MINUTOS * 60)

    except KeyboardInterrupt:
        print("Captura detenida por el usuario.")

if __name__ == "__main__":
    main()
