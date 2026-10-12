import os
import shutil
import subprocess
import time
from flask import Flask, render_template_string, request, jsonify, send_file

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave-secreta-por-defecto")

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
            max-height: 180px;
            overflow-y: auto;
            border-radius: 6px;
            padding: 10px;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
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

                            <div class="mb-3">
                                <label for="download-path" class="form-label fw-bold">Carpeta de destino preferida (Opcional):</label>
                                <input type="text" class="form-control" id="download-path" name="custom_path" 
                                       placeholder="Ej: Descargas/MusicaHRA">
                            </div>
                            
                            <!-- Panel de estimaciones -->
                            <div id="info-panel" class="alert alert-secondary d-none mb-3">
                                <ul class="mb-0 small">
                                    <li><strong>Tamaño estimado:</strong> <span id="est-size">Calculando...</span></li>
                                    <li><strong>Tiempo estimado de espera:</strong> <span id="est-time">Calculando...</span></li>
                                </ul>
                            </div>

                            <!-- Cuadro de avance individual en tiempo real -->
                            <div id="progress-container" class="mb-3 d-none">
                                <label class="text-primary fw-bold mb-1">Progreso y estado de la conexión:</label>
                                <div id="console-output" class="console-box mb-2">Iniciando descarga en alta fidelidad...</div>
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
            const customPath = document.getElementById('download-path').value;
            const progressContainer = document.getElementById('progress-container');
            const btnContainer = document.getElementById('btn-container');
            const alertContainer = document.getElementById('alert-container');
            const consoleBox = document.getElementById('console-output');
            
            alertContainer.innerHTML = '';
            consoleBox.innerHTML = '>> Conectando con el servidor y extrayendo pistas...\\n';
            progressContainer.classList.remove('d-none');
            btnContainer.classList.add('d-none');

            try {
                // Usamos un controlador con timeout extendido a 9 minutos en el cliente JavaScript
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 540000);

                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: 'url=' + encodeURIComponent(urlInput) + '&custom_path=' + encodeURIComponent(customPath),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (response.ok) {
                    consoleBox.innerHTML += '>> ¡Paquete ZIP listo! Transfiriendo archivo al navegador...\\n';
                    const blob = await response.blob();
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = "Musica_HRA.zip";
                    document.body.appendChild(a);
                    a.click();
                    a.remove();

                    progressContainer.classList.add('d-none');
                    btnContainer.classList.remove('d-none');
                    alertContainer.innerHTML = `
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            ¡Descarga completada con éxito en tu navegador!
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>`;
                    document.getElementById('url').value = '';
                    document.getElementById('info-panel').classList.add('d-none');
                } else {
                    const data = await response.json();
                    progressContainer.classList.add('d-none');
                    btnContainer.classList.remove('d-none');
                    alertContainer.innerHTML = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            ${data.message || "Error desconocido en el proceso."}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>`;
                }
            } catch (error) {
                progressContainer.classList.add('d-none');
                btnContainer.classList.remove('d-none');
                let errText = "Error de conexión persistente con el servidor.";
                if (error.name === 'AbortError') {
                    errText = "La descarga tardó demasiado tiempo y el navegador canceló la solicitud.";
                }
                alertContainer.innerHTML = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        ${errText}
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

@app.route("/download", methods=["POST"])
def download():
    song_url = request.form.get("url")
    
    if not song_url:
        return jsonify({"success": False, "message": "Por favor, introduce un enlace válido."}), 400

    download_dir = os.path.join(os.getcwd(), "downloads")
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    try:
        # Invocación con python3 corregido y tiempo límite de 500 segundos
        process = subprocess.run(
            ["python3", "HRA-DL.py", "--url", song_url],
            capture_output=True,
            text=True,
            timeout=500
        )

        if process.returncode != 0:
            error_message = process.stderr.strip() or process.stdout.strip() or "Error desconocido."
            return jsonify({"success": False, "message": f"Error en el proceso: {error_message}"}), 500

        target_folder = download_dir if os.path.exists(download_dir) and os.listdir(download_dir) else os.getcwd()
        
        # Filtro interno estricto
        allowed_extensions = ('.flac', '.jpg', '.jpeg', '.png')
        for root, dirs, files in os.walk(target_folder):
            for file in files:
                if not file.lower().endswith(allowed_extensions):
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception:
                        pass

        # Normalización de timestamps para evitar errores de ZIP en Linux
        current_time = time.time()
        for root, dirs, files in os.walk(target_folder):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.utime(file_path, (current_time, current_time))
                except Exception:
                    pass

        zip_filename = "HRA_Download"
        zip_path = shutil.make_archive(zip_filename, 'zip', target_folder)

        return send_file(zip_path, as_attachment=True, download_name="Musica_HRA.zip")

    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "message": "La descarga ha superado el tiempo límite del servidor y se ha detenido."}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Ocurrió un error inesperado: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
