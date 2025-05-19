from app import create_app
from watchdog_wifi import iniciar_watchdog

app = create_app()

iniciar_watchdog() # Iniciar el monitoreo de Wifi

if __name__ == '__main__':
    app.run(debug=True)