import time
from capturar_imagenes import capturar_y_guardar

INTERVALO_MINUTOS = 15

if __name__ == "__main__":
    try:
        while True:
            print("Capturando imagen...")
            capturar_y_guardar()
            print(f"Esperando {INTERVALO_MINUTOS} minutos...")
            time.sleep(INTERVALO_MINUTOS * 60)
    except KeyboardInterrupt:
        print("Captura detenida por el usuario.")
