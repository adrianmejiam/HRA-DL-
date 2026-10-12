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
</head>
<body class="bg-light d-flex flex-column min-vh-100">
    <div class="container py-5 my-auto">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow-sm">
                    <div class="card-header bg-dark text-white text-center py-3">
                        <h3 class="mb-0">HighResAudio Downloader</h3>
                        <small class="text-muted">Descarga música en alta resolución directamente a tu dispositivo</small>
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
                                <label for="download-path" class="form-label font-weight-bold">Carpeta de destino preferida (Opcional):</label>
                                <input type="text" class="form-control" id="download-path" name="custom_path" 
                                       placeholder="Ej: Descargas/MusicaHRA (El navegador usará tu carpeta predeterminada si se deja vacío)">
                                <div class="form-text">Los archivos se empaquetarán en un ZIP listo para tu navegador.</div>
                            </div>
                            
                            <!-- Panel de estimaciones -->
                            <div id="info-panel" class="alert alert-secondary d-none mb-3">
                                <ul class="mb-0 small">
                                    <li><strong>Tamaño estimado:</strong> <span id="est-size">Calculando...</span></li>
                                    <li><strong>Tiempo estimado de espera:</strong> <span id="est-time">Calculando...</span></li>
                                </ul>
                            </div>

                            <div id="progress-container" class="mb-3 d-none">
                                <label class="form-label text-primary fw-bold" id="status-text">Descargando y preparando archivos...</label>
                                <div class="progress" style="height: 25px;">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                                         role="progressbar" style="width: 100%;" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100">
                                        Por favor, espera unos segundos...
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
                    Desarrollado por <strong>adrianmejiam</strong> | &copy; 2026
                </div>
            </div>
        </div>
    </div>

    <script>
        // Estimaciones dinámicas basadas en el enlace introducido
        document.getElementById('url').addEventListener('input', function(e) {
            const val = e.target.value;
            const infoPanel = document.getElementById('info-panel');
            if (val.includes('album')) {
                document.getElementById('est-size').textContent = 'Aprox. 350 MB - 1.2 GB (FLAC Lossless)';
                document.getElementById('est-time').textContent = '1 a 3 minutos (dependiendo de la conexión)';
                infoPanel.classList.remove('d-none');
            } else if (val.includes('track') || val.includes('title')) {
                document.getElementById('est-size').textContent = 'Aprox. 35 MB - 120 MB';
                document.getElementById('est-time').textContent = '15 a 30 segundos';
                infoPanel.classList.remove('d-none');
            } else {
                infoPanel.classList.add('d-none');
            }
        });

        // Manejo del formulario y descarga del archivo ZIP
        document.getElementById('download-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const urlInput = document.getElementById('url').value;
            const customPath = document.getElementById('download-path').value;
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
                    body: 'url=' + encodeURIComponent(urlInput) + '&custom_path=' + encodeURIComponent(customPath)
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = "HRA_Music_Download.zip";
                    document.body.appendChild(a);
                    a.click();
                    a.remove();

                    progressContainer.classList.add('d-none');
                    btnContainer.classList.remove('d-none');
                    alertContainer.innerHTML = `
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            ¡Descarga completada y enviada a tu navegador con éxito!
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
    custom_path = request.form.get("custom_path", "").strip()
    
    if not song_url:
        return jsonify({"success": False, "message": "Por favor, introduce un enlace válido."}), 400

    download_dir = os.path.join(os.getcwd(), "downloads")
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    try:
        process = subprocess.run(
            ["python", "HRA-DL.py", "--url", song_url],
            capture_output=True,
            text=True,
            timeout=300
        )

        if process.returncode != 0:
            error_message = process.stderr.strip() or process.stdout.strip() or "Error desconocido."
            return jsonify({"success": False, "message": f"Error en el proceso: {error_message}"}), 500

        target_folder = download_dir if os.path.exists(download_dir) and os.listdir(download_dir) else os.getcwd()
        
        # SOLUCIÓN AL ERROR DE TIMESTAMPS ANTERIORES A 1980:
        # Actualizamos la fecha de acceso y modificación de todos los archivos encontrados al momento actual
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
        return jsonify({"success": False, "message": "La descarga ha tardado más de 5 minutos y se ha interrumpido."}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Ocurrió un error inesperado: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
