import threading
import time
import json
import sqlite3
from datetime import datetime
import serial
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# CAMBIA ESTO POR EL PUERTO COM DE TU ARDUINO RECEPTOR (ej. 'COM3', 'COM4', etc.)
PUERTO_USB = 'COM3' 
BAUDIOS = 9600
DB_NAME = 'datos.db'

ultimo_dato = {
    "temperatura": 0.0,
    "presion": 0.0,
    "altitud": 0.0,
    "humedad": "N/A (BMP280)",
    "hora": "Esperando datos..."
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lecturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT,
            temperatura REAL,
            presion REAL,
            altitud REAL
        )
    ''')
    conn.commit()
    conn.close()

def leer_arduino():
    global ultimo_dato
    while True:
        try:
            ser = serial.Serial(PUERTO_USB, BAUDIOS, timeout=2)
            print(f"Conectado al Arduino en {PUERTO_USB}")
            time.sleep(2) # Esperar a que el Arduino se reinicie al abrir el puerto
            
            while True:
                if ser.in_waiting > 0:
                    linea = ser.readline().decode('utf-8', errors='ignore').strip()
                    print(f"Recibido: {linea}")
                    
                    try:
                        datos = json.loads(linea)
                        ahora = datetime.now().strftime("%H:%M:%S")
                        
                        temp = float(datos.get("temp", 0))
                        pres = float(datos.get("pres", 0))
                        alt = float(datos.get("alt", 0))
                        
                        ultimo_dato = {
                            "temperatura": temp,
                            "presion": pres,
                            "altitud": alt,
                            "humedad": "N/A (Solo BMP280)",
                            "hora": ahora
                        }
                        
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO lecturas (fecha_hora, temperatura, presion, altitud) VALUES (?, ?, ?, ?)",
                            (ahora, temp, pres, alt)
                        )
                        conn.commit()
                        conn.close()
                        
                    except json.JSONDecodeError:
                        pass
                        
        except serial.SerialException:
            print(f"No se puede abrir {PUERTO_USB}. Verifica que el Monitor Serie de Arduino esté cerrado.")
            time.sleep(5)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/actual')
def api_actual():
    return jsonify(ultimo_dato)

@app.route('/api/historial')
def api_historial():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT fecha_hora, temperatura, presion, altitud FROM lecturas ORDER BY id DESC LIMIT 15")
    filas = cursor.fetchall()
    conn.close()
    
    filas.reverse()
    return jsonify({
        "horas": [f[0] for f in filas],
        "temperaturas": [f[1] for f in filas],
        "presiones": [f[2] for f in filas],
        "altitudes": [f[3] for f in filas]
    })

if __name__ == '__main__':
    init_db()
    hilo_serial = threading.Thread(target=leer_arduino, daemon=True)
    hilo_serial.start()
    app.run(host='0.0.0.0', port=5000, debug=False)