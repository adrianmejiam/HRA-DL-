import os
import shutil
import subprocess
import time
import threading
from flask import Flask, render_template_string, request, jsonify, send_file, Response

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave-secreta-por-defecto")

# Diccionario global temporal para almacenar los logs de descarga por sesión
download_logs = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HRA-DL Web Downloader</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .brand-header {
            background: linear-gradient(135deg, #121212 0%, #2c2c2c 100%);
            border-bottom: 3px solid #d4af37;
        }
        .hires-logo {
            width: 45px;
            height: 45px;
            object-fit: contain;
            margin-right: 12px;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .console-box {
            background-color: #121212;
            color: #00ff66;
            font-family: monospace;
            font-size: 0.85rem;
            height: 200px;
            overflow-y: auto;
            border-radius: 6px;
            padding: 10px;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
            white-space: pre-wrap;
            word-break: break-all;
        }
    </style>
</head>
<body class="bg-light d-flex flex-column min-vh-100">
    <div class="container py-5 my-auto">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow-lg border-0">
                    <div class="card-header brand-header text-white text-center py-4">
                        <div class="d-flex align-items-center justify-content-center">
                            <img src="https://thumb.wikimedia.org/wikipedia/en/thumb/d/d1/Hi-Res_Audio_%28logo%29.svg/1280px-Hi-Res_Audio_%28logo%29.svg.png" 
                                 alt="Hi-Res Audio Logo" class="hires-logo">
                            <h2 class="mb-0 fw-bold tracking-wide text-warning">HIGH RES AUDIO</h2>
                        </div>
                        <p class="text-light small mt-2 mb-0 opacity-75">Sistema Automatizado de Descarga Directa en Máxima Fidelidad</p>
                    </div>
                    <div class="card-body p-4">
                        <div id="alert-container"></div>

                        <form id="download-form">
                            <div class="mb-3">
                                <label for="url" class="form-label fw-bold">Enlace del Álbum o Pista de HighResAudio:</label>
                                <input type="url" class="form-control form-control-lg" id="url" name="url" required 
                                       placeholder="https://www.highresaudio.com/es/album/artist/name-album">
                            </div>
                            
                            <!-- Panel de estimaciones -->
                            <div id="info-panel" class="alert alert-secondary d-none mb-3">
                                <ul class="mb-0 small">
                                    <li><strong>Tamaño estimado:</strong> <span id="est-size">Calculando...</span></li>
                                    <li><strong>Tiempo estimado de espera:</strong> <span id="est-time">Calculando...</span></li>
                                </ul>
                            </div>

                            <!-- Cuadro de la interfaz del script en tiempo real -->
                            <div id="progress-container" class="mb-3 d-none">
                                <label class="text-primary fw-bold mb-1">Consola de Descarga (Progreso individual):</label>
                                <div id="console-output" class="console-box mb-2">Inicializando...</div>
                                <div class="progress" style="height: 15px;">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-warning" 
                                         role="progressbar" style="width: 100%;" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"></div>
                                </div>
                            </div>

                            <div class="d-grid" id="btn-container">
                                <button type="submit" id="submit-btn" class="btn btn-warning btn-lg fw-bold text-dark shadow-sm">Iniciar Descarga Segura</button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Créditos del Desarrollador -->
                <div class="text-center mt-4 text-muted small">
                    Desarrollado por <strong>adrianmejiam</strong> | &copy; 2026
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('url').addEventListener('input', function(e) {
            const val = e.target.value;
            const infoPanel = document.getElementById('info-panel');
            if (val.includes('album')) {
                document.getElementById('est-size').textContent = 'Aprox. 350 MB - 1.2 GB (Lossless)';
                document.getElementById('est-time').textContent = '1 a 3 minutos';
                infoPanel.classList.remove('d-none');
            } else if (val.includes('track') || val.includes('title')) {
                document.getElementById('est-size').textContent = 'Aprox. 35 MB - 120 MB';
                document.getElementById('est-time').textContent = '15 a 30 segundos';
                infoPanel.classList.remove('d-none');
            } else {
                infoPanel.classList.add('d-none');
            }
        });

        document.getElementById('download-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const urlInput = document.getElementById('url').value;
            const progressContainer = document.getElementById('progress-container');
            const btnContainer = document.getElementById('btn-container');
            const alertContainer = document.getElementById('alert-container');
            const consoleBox = document.getElementById('console-output');
            
            alertContainer.innerHTML = '';
            consoleBox.innerHTML = '>> Se estableció conexión con el servidor.\\n';
            progressContainer.classList.remove('d-none');
            btnContainer.classList.add('d-none');

            try {
                // Iniciamos la petición de descarga en el servidor
                const response = await fetch('/start-download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'url=' + encodeURIComponent(urlInput)
                });

                const data = await response.json();
                if (!data.success) {
                    throw new Error(data.message);
                }

                const sessionId = data.session_id;

                // Conectamos al canal de eventos en tiempo real para leer la consola del script
                const eventSource = new EventSource(`/stream-logs/${sessionId}`);
                
                eventSource.onmessage = function(event) {
                    if (event.data === "[DONE]") {
                        eventSource.close();
                        // Descargar el archivo ZIP generado automáticamente
                        window.location.href = `/get-zip/${sessionId}`;
                        progressContainer.classList.add('d-none');
                        btnContainer.classList.remove('d-none');
                        alertContainer.innerHTML = `
                            <div class="alert alert-success alert-dismissible fade show" role="alert">
                                ¡Descarga completada con éxito y enviada a tu navegador!
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>`;
                        document.getElementById('url').value = '';
                        document.getElementById('info-panel').classList.add('d-none');
                    } else if (event.data.startsWith("[ERROR]")) {
                        eventSource.close();
                        progressContainer.classList.add('d-none');
                        btnContainer.classList.remove('d-none');
                        alertContainer.innerHTML = `
                            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                                ${event.data.replace("[ERROR]", "")}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>`;
                    } else {
                        consoleBox.textContent += event.data + "\\n";
                        consoleBox.scrollTop = consoleBox.scrollHeight;
                    }
                };

                eventSource.onerror = function() {
                    eventSource.close();
                };

            } catch (error) {
                progressContainer.classList.add('d-none');
                btnContainer.classList.remove('d-none');
                alertContainer.innerHTML = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        ${error.message || "Ocurrió un error de comunicación con el servidor."}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>`;
            }
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

def run_download_process(session_id, song_url):
    download_logs[session_id] = []
    
    download_dir = os.path.join(os.getcwd(), f"downloads_{session_id}")
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, "HRA-DL.py")

        # Ejecutamos el script leyendo su salida estándar línea por línea en tiempo real
        process = subprocess.Popen(
            ["python3", script_path, "--url", song_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=download_dir
        )

        for line in process.stdout:
            clean_line = line.strip()
            if clean_line:
                download_logs[session_id].append(clean_line)

        process.wait()

        if process.returncode != 0:
            download_logs[session_id].append("[ERROR] Error en el proceso de descarga del script.")
            return

        # Filtro interno estricto (solo FLAC, JPG, JPEG, PNG)
        allowed_extensions = ('.flac', '.jpg', '.jpeg', '.png')
        for root, dirs, files in os.walk(download_dir):
            for file in files:
                if not file.lower().endswith(allowed_extensions):
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception:
                        pass

        # Normalización de timestamps para evitar el error de ZIP antes de 1980 en Linux
        current_time = time.time()
        for root, dirs, files in os.walk(download_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.utime(file_path, (current_time, current_time))
                except Exception:
                    pass

        # Crear archivo ZIP final de la sesión
        zip_path = os.path.join(os.getcwd(), f"HRA_Download_{session_id}")
        shutil.make_archive(zip_path, 'zip', download_dir)
        download_logs[session_id].append("[DONE]")

    except Exception as e:
        download_logs[session_id].append(f"[ERROR] Ocurrió un error inesperado: {str(e)}")

@app.route("/start-download", methods=["POST"])
def start_download():
    song_url = request.form.get("url")
    if not song_url:
        return jsonify({"success": False, "message": "Por favor, introduce un enlace válido."}), 400

    session_id = str(time.time_ns())
    
    # Lanzar el proceso de descarga en un hilo independiente en segundo plano
    thread = threading.Thread(target=run_download_process, args=(session_id, song_url))
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "session_id": session_id})

@app.route("/stream-logs/<session_id>")
def stream_logs(session_id):
    def generate():
        index = 0
        while True:
            if session_id in download_logs:
                logs = download_logs[session_id]
                while index < len(logs):
                    log_line = logs[index]
                    yield f"data: {log_line}\n\n"
                    if log_line == "[DONE]" or log_line.startswith("[ERROR]"):
                        return
                    index += 1
            time.sleep(0.5)

    return Response(generate(), mimetype="text/event-stream")

@app.route("/get-zip/<session_id>")
def get_zip(session_id):
    zip_filename = f"HRA_Download_{session_id}.zip"
    if os.path.exists(zip_filename):
        return send_file(zip_filename, as_attachment=True, download_name="Musica_HRA.zip")
    return jsonify({"success": False, "message": "Archivo no encontrado."}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
