import os
import subprocess
from flask import Flask, render_template_string, request, jsonify

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
        .clock-badge {
            font-family: monospace;
            font-size: 0.9rem;
            background-color: #212529;
            color: #0d6efd;
            padding: 5px 12px;
            border-radius: 20px;
            display: inline-block;
            box-shadow: inset 0 0 5px rgba(0,0,0,0.5);
        }
    </style>
</head>
<body class="bg-light d-flex flex-column min-vh-100">
    <div class="container py-5 my-auto">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <!-- Encabezado con Reloj -->
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <span class="text-muted small">HighResAudio Automated System</span>
                    <div id="live-clock" class="clock-badge">00:00:00</div>
                </div>

                <div class="card shadow-sm">
                    <div class="card-header bg-dark text-white text-center py-3">
                        <h3 class="mb-0">HighResAudio Downloader</h3>
                        <small class="text-muted">Descarga música en alta resolución con formato y metadatos personalizados</small>
                    </div>
                    <div class="card-body p-4">
                        <div id="alert-container"></div>

                        <form id="download-form">
                            <div class="mb-3">
                                <label for="url" class="form-label font-weight-bold">Enlace del Álbum o Pista de HighResAudio:</label>
                                <input type="url" class="form-control" id="url" name="url" required 
                                       placeholder="https://www.highresaudio.com/es/album/artist/name-album">
                            </div>

                            <div class="mb-3">
                                <label for="format" class="form-label font-weight-bold">Formato de audio:</label>
                                <select class="form-select" id="format" name="format">
                                    <option value="flac" selected>FLAC (Sin pérdida - Recomendado)</option>
                                    <option value="wav">WAV (Sin comprimir)</option>
                                </select>
                            </div>
                            
                            <div id="progress-container" class="mb-3 d-none">
                                <label class="form-label text-primary fw-bold" id="status-text">Procesando descarga...</label>
                                <div class="progress" style="height: 25px;">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                                         role="progressbar" style="width: 100%;" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100">
                                        Descargando y convirtiendo archivos...
                                    </div>
                                </div>
                            </div>

                            <div class="d-grid" id="btn-container">
                                <button type="submit" id="submit-btn" class="btn btn-primary btn-lg">Iniciar Descarga</button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Créditos del Desarrollador -->
                <div class="text-center mt-4 text-muted small">
                    Desarrollado con ❤️ para amantes de la música en alta fidelidad | &copy; 2026
                </div>
            </div>
        </div>
    </div>

    <script>
        // Función del reloj en tiempo real
        function updateClock() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('live-clock').textContent = `${hours}:${minutes}:${seconds}`;
        }
        setInterval(updateClock, 1000);
        updateClock();

        // Control de envío por formulario asíncrono
        document.getElementById('download-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const urlInput = document.getElementById('url').value;
            const formatInput = document.getElementById('format').value;
            const progressContainer = document.getElementById('progress-container');
            const btnContainer = document.getElementById('btn-container');
            const alertContainer = document.getElementById('alert-container');
            
            alertContainer.innerHTML = '';
            progressContainer.classList.remove('d-none');
            btnContainer.classList.add('d-none');

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: 'url=' + encodeURIComponent(urlInput) + '&format=' + encodeURIComponent(formatInput)
                });

                const data = await response.json();

                progressContainer.classList.add('d-none');
                btnContainer.classList.remove('d-none');

                if (data.success) {
                    alertContainer.innerHTML = `
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            ${data.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>`;
                    document.getElementById('url').value = '';
                } else {
                    alertContainer.innerHTML = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            ${data.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>`;
                }
            } catch (error) {
                progressContainer.classList.add('d-none');
                btnContainer.classList.remove('d-none');
                alertContainer.innerHTML = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        Ocurrió un error de red o de comunicación con el servidor.
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
    audio_format = request.form.get("format", "flac")
    
    if not song_url:
        return jsonify({"success": False, "message": "Por favor, introduce un enlace válido."})

    try:
        process = subprocess.run(
            ["python", "HRA-DL.py", "--url", song_url, "--format", audio_format],
            capture_output=True,
            text=True,
            timeout=300
        )

        if process.returncode == 0:
            return jsonify({"success": True, "message": f"¡Descarga completada con éxito en formato {audio_format.upper()}!"})
        else:
            error_message = process.stderr.strip() or process.stdout.strip() or "Error desconocido durante la ejecución."
            return jsonify({"success": False, "message": f"Error en el proceso: {error_message}"})

    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "message": "La descarga ha tardado más de 5 minutos y se ha interrumpido por tiempo límite."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Ocurrió un error inesperado: {str(e)}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
