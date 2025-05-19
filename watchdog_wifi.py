import threading
import time
import os
import socket
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def restart_wifi_windows(interface_name="Wi-Fi"):
    log("❌ Internet desconectado. Reiniciando WiFi...")
    os.system(f'netsh interface set interface name="{interface_name}" admin=disable')
    time.sleep(5)
    os.system(f'netsh interface set interface name="{interface_name}" admin=enable')
    log("✅ WiFi reconectado.")

def watchdog_wifi(interface_name="Wi-Fi", check_interval=900):
    while True:
        if not check_internet():
            restart_wifi_windows(interface_name)
        else:
            log("✅ Conexión a Internet activa.")
        time.sleep(check_interval)

# Inicia el watchdog como un hilo en segundo plano
def iniciar_watchdog():
    t = threading.Thread(target=watchdog_wifi, daemon=True)
    t.start()
