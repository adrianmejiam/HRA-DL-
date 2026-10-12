import os
import shutil
import subprocess
import time
import threading
from flask import Flask, render_template_string, request, jsonify, send_file, Response, after_this_request

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave-secreta-por-defecto")

# Diccionario global para almacenar los logs y metadatos de las sesiones de descarga
download_logs = {}
session_metadata = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HRA-DL Web Downloader - Máxima Fidelidad</title>
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
            height: 150px;
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
            <div class="col-md-10">
                <!-- Navegación por pestañas -->
                <ul class="nav nav-tabs mb-4 justify-content-center fw-bold" id="mainTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active text-dark" id="download-tab" data-bs-toggle="tab" data-bs-target="#download-pane" type="button" role="tab">Nueva Descarga</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link text-dark" id="monitor-tab" data-bs-toggle="tab" data-bs-target="#monitor-pane" type="button" role="tab" onclick="refreshActiveDownloads()">Panel de Avance y Descargas</button>
                    </li>
                </ul>

                <div class="tab-content" id="mainTabsContent">
                    <!-- PESTAÑA 1: NUEVA DESCARGA -->
                    <div class="tab-pane fade show active" id="download-pane" role="tabpanel">
                        <div class="card shadow-lg border-0">
                            <div class="card-header brand-header text-white text-center py-4">
                                <div class="d-flex align-items-center justify-content-center">
                                    <img src="https://thumb.wikimedia.org/wikipedia/en/thumb/d/d1/Hi-Res_Audio_%28logo%29.svg/1280px-Hi-Res_Audio_%28logo%29.svg.png" 
                                         alt="Hi-Res Audio Logo" class="hires-logo">
                                    <h2 class="mb-0 fw-bold tracking-wide text-warning">HIGHRESAUDIO</h2>
                                </div>
                                <p class="text-light small mt-2 mb-0 opacity-75">Descarga Directa Lossless en Máxima Fidelidad (Sin Pérdida)</p>
                            </div>
                            <div class="card-body p-4">
                                <div id="alert-container"></div>

                                <form id="download-form">
                                    <div class="mb-3">
                                        <label for="url" class="form-label fw-bold">Enlace del Álbum o Pista de HIGHRESAUDIO.com:</label>
                                        <input type="url" class="form-control form-control-lg" id="url" name="url" required 
                                               placeholder="https://www.highresaudio.com/es/album/artist/name-album">
                                    </div>

                                    <!-- Credenciales de HIGHRESAUDIO -->
                                    <div class="card bg-light border mb-3">
                                        <div class="card-body p-3">
                                            <h6 class="fw-bold text-dark mb-2">Autenticación de Cuenta HIGHRESAUDIO (Opcional):</h6>
                                            <div class="row g-2">
                                                <div class="col-md-6">
                                                    <label for="email" class="form-label small fw-bold text-muted mb-1">Correo Electrónico:</label>
                                                    <input type="email" class="form-control form-control-sm" id="email" name="email" 
                                                           placeholder="usuario@ejemplo.com">
                                                </div>
                                                <div class="col-md-6">
                                                    <label for="password" class="form-label small fw-bold text-muted mb-1">Contraseña:</label>
                                                    <input type="password" class="form-control form-control-sm" id="password" name="password" 
                                                           placeholder="••••••••">
                                                </div>
                                            </div>
                                            <div class="mt-2">
                                                <label for="cookie" class="form-label small fw-bold text-muted mb-1">O usar Cookie / Token de Sesión directo:</label>
                                                <input type="text" class="form-control form-control-sm" id="cookie" name="cookie" 
                                                       placeholder="Pega tu cookie de sesión si prefieres no ingresar tus credenciales">
                                            </div>
                                        </div>
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
                                        <label class="text-primary fw-bold mb-1">Consola de Descarga Lossless:</label>
                                        <div id="console-output" class="console-box mb-2">Inicializando...</div>
                                        <div class="progress" style="height: 15px;">
                                            <div class="progress-bar progress-bar-striped progress-bar-animated bg-warning" 
                                                 role="progressbar" style="width: 100%;" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"></div>
                                        </div>
                                    </div>

                                    <div class="d-grid" id="btn-container">
                                        <button type="submit" id="submit-btn" class="btn btn-warning btn-lg fw-bold text-dark shadow-sm">Iniciar Descarga en Máxima Fidelidad</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>

                    <!-- PESTAÑA 2: PANEL DE AVANCE Y DESCARGAS -->
                    <div class="tab-pane fade" id="monitor-pane" role="tabpanel">
                        <div class="card shadow-lg border-0">
                            <div class="card-header bg-dark text-white py-3 d-flex justify-content-between align-items-center">
                                <h5 class="mb-0 text-warning fw-bold">Panel de Monitoreo de Descargas Activas</h5>
                                <button class="btn btn-sm btn-outline-light" onclick="refreshActiveDownloads()">Actualizar Lista</button>
                            </div>
                            <div class="card-body p-4">
                                <div id="active-downloads-list">
                                    <p class="text-muted text-center">Cargando sesiones activas...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Créditos del Desarrollador -->
                <div class="text-center mt-4 text-muted small">
                    Desarrollado por <strong>adrianmejiam</strong> | &copy; 2026
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('url').addEventListener('input', function(e) {
            const val = e.target.value;
            const infoPanel = document.getElementById('info-panel');
            if (val.includes('album')) {
                document.getElementById('est-size').textContent = 'Aprox. 350 MB - 1.5 GB (FLAC Lossless)';
                document.getElementById('est-time').textContent = '1 a 3 minutos';
                infoPanel.classList.remove('d-none');
            } else if (val.includes('track') || val.includes('title')) {
                document.getElementById('est-size').textContent = 'Aprox. 35 MB - 150 MB (FLAC Lossless)';
                document.getElementById('est-time').textContent = '15 a 30 segundos';
                infoPanel.classList.remove('d-none');
            } else {
                infoPanel.classList.add('d-none');
            }
        });

        document.getElementById('download-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const urlInput = document.getElementById('url').value;
            const emailInput = document.getElementById('email').value;
            const passwordInput = document.getElementById('password').value;
            const cookieInput = document.getElementById('cookie').value;
            
            const progressContainer = document.getElementById('progress-container');
            const btnContainer = document.getElementById('btn-container');
            const alertContainer = document.getElementById('alert-container');
            const consoleBox = document.getElementById('console-output');
            
            alertContainer.innerHTML = '';
            consoleBox.innerHTML = '>> Conectando con HIGHRESAUDIO.com...\\n';
            progressContainer.classList.remove('d-none');
            btnContainer.classList.add('d-none');

            try {
                const response = await fetch('/start-download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'url=' + encodeURIComponent(urlInput) + 
                          '&email=' + encodeURIComponent(emailInput) + 
                          '&password=' + encodeURIComponent(passwordInput) + 
                          '&cookie=' + encodeURIComponent(cookieInput)
                });

                const data = await response.json();
                if (!data.success) {
                    throw new Error(data.message);
                }

                const sessionId = data.session_id;
                const eventSource = new EventSource(`/stream-logs/${sessionId}`);
                
                eventSource.onmessage = function(event) {
                    if (event.data === "[DONE]") {
                        eventSource.close();
                        window.location.href = `/get-zip/${sessionId}`;
                        progressContainer.classList.add('d-none');
                        btnContainer.classList.remove('d-none');
                        alertContainer.innerHTML = `
                            <div class="alert alert-success alert-dismissible fade show" role="alert">
                                ¡Descarga Lossless completada y empaquetada con éxito!
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>`;
                        document.getElementById('url').value = '';
                        document.getElementById('email').value = '';
                        document.getElementById('password').value = '';
                        document.getElementById('cookie').value = '';
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

        async function refreshActiveDownloads() {
            const container = document.getElementById('active-downloads-list');
            container.innerHTML = '<p class="text-muted text-center">Actualizando estado...</p>';

            try {
                const response = await fetch('/api/sessions');
                const data = await response.json();

                if (!data.sessions || data.sessions.length === 0) {
                    container.innerHTML = '<p class="text-muted text-center mb-0">No hay descargas registradas o activas actualmente.</p>';
                    return;
                }

                let html = '<div class="list-group">';
                data.sessions.forEach(s => {
                    let badgeClass = 'bg-secondary';
                    let statusText = s.status;
                    if (s.status === 'Procesando...') badgeClass = 'bg-warning text-dark';
                    else if (s.status === 'Completado') badgeClass = 'bg-success';
                    else if (s.status.includes('Error')) badgeClass = 'bg-danger';

                    html += `
                        <div class="list-group-item list-group-item-action flex-column align-items-start mb-2 rounded shadow-sm border">
                            <div class="d-flex w-100 justify-content-between">
                                <h6 class="mb-1 text-truncate" style="max-width: 70%;"><strong>URL:</strong> ${s.url}</h6>
                                <span class="badge ${badgeClass} align-self-center">${statusText}</span>
                            </div>
                            <p class="mb-1 small text-muted text-truncate">Último registro: ${s.last_log}</p>
                            <div class="d-flex justify-content-between align-items-center mt-2">
                                <small class="text-muted">ID: ${s.session_id}</small>
                                ${s.ready_to_download ? `<a href="/get-zip/${s.session_id}" class="btn btn-sm btn-success fw-bold">Descargar ZIP</a>` : ''}
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                container.innerHTML = html;
            } catch (error) {
                container.innerHTML = '<p class="text-danger text-center">Error al conectar con el servidor para obtener las sesiones.</p>';
            }
        }

        setInterval(() => {
            const monitorTab = document.getElementById('monitor-pane');
            if (monitorTab && monitorTab.classList.contains('active')) {
                refreshActiveDownloads();
            }
        }, 5000);
    </script>
</body>
</html>
"""

def background_cleanup_janitor():
    while True:
        time.sleep(1800)
        now = time.time()
        try:
            for item in os.listdir(os.getcwd()):
                item_path = os.path.join(os.getcwd(), item)
                if item.startswith("HRA_Download_") and item.endswith(".zip"):
                    if os.path.isfile(item_path) and (now - os.path.getmtime(item_path) > 1800):
                        os.remove(item_path)
                elif item.startswith("downloads_") and os.path.isdir(item_path):
                    if now - os.path.getmtime(item_path) > 1800:
                        shutil.rmtree(item_path, ignore_errors=True)
        except Exception:
            pass

janitor_thread = threading.Thread(target=background_cleanup_janitor, daemon=True)
janitor_thread.start()

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

def run_download_process(session_id, song_url, email, password, cookie_data):
    download_logs[session_id] = []
    session_metadata[session_id] = {
        "url": song_url,
        "status": "Procesando...",
        "last_log": "Autenticando e iniciando descarga...",
        "ready_to_download": False
    }
    
    download_dir = os.path.join(os.getcwd(), f"downloads_{session_id}")
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, "HRA-DL.py")

        env = os.environ.copy()
        
        if email:
            env["HRA_USERNAME"] = email
            env["HRA_EMAIL"] = email
        if password:
            env["HRA_PASSWORD"] = password

        if cookie_data:
            env["HRA_COOKIE"] = cookie_data
            cookie_file_path = os.path.join(base_dir, "cookies.txt")
            with open(cookie_file_path, "w", encoding="utf-8") as f:
                f.write(cookie_data)

        cmd = ["python3", script_path, "--url", song_url]
        if email and password:
            cmd.extend(["-u", email, "-p", password])

        # Llamada a Popen optimizada y con paréntesis correctamente cerrados
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.S
