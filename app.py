import os
import subprocess
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Variable global para rastrear si hay una descarga activa
current_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start-download', methods=['POST'])
def start_download():
    global current_process
    
    # Verificar si ya hay un proceso corriendo
    if current_process and current_process.poll() is None:
        return jsonify({"status": "error", "message": "Ya hay una descarga en curso."}), 400

    data = request.json
    email = data.get('email')
    password = data.get('password')
    quality = data.get('quality', 'flac-hi-res')
    download_path = data.get('path', './downloads')
    cover = data.get('cover', False)

    # Validar campos obligatorios
    if not email or not password:
        return jsonify({"status": "error", "message": "El correo y la contraseña son obligatorios."}), 400

    # Crear la carpeta de descargas si no existe
    os.makedirs(download_path, exist_ok=True)

    # Construir la lista de argumentos para subprocess
    cmd = [
        'python', 'HRA-DL.py',
        '--email', email,
        '--password', password,
        '--quality', quality,
        '--path', download_path
    ]
    
    if cover:
        cmd.append('--cover')

    try:
        # Ejecutar el script en segundo plano
        current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return jsonify({"status": "success", "message": "¡Descarga iniciada correctamente!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def check_status():
    global current_process
    if current_process is None:
        return jsonify({"status": "idle", "message": "Inactivo"})
    
    poll = current_process.poll()
    if poll is None:
        return jsonify({"status": "running", "message": "Descargando música..."})
    else:
        if poll == 0:
            return jsonify({"status": "completed", "message": "Descarga finalizada con éxito."})
        else:
            stderr_output = current_process.stderr.read() if current_process.stderr else "Error desconocido"
            return jsonify({"status": "failed", "message": f"La descarga falló: {stderr_output}"})

if __name__ == '__main__':
    # Se ejecuta de manera local en el puerto 5000 (accesible también vía Termux o navegador)
    app.run(host='0.0.0.0', port=5000, debug=True)
