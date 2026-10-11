import os
import subprocess
from flask import Flask, render_template_string, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave-secreta-por-defecto")

# Plantilla HTML integrada para la interfaz web con estilos modernos de Bootstrap
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HRA-DL Web Downloader</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow-sm">
                    <div class="card-header bg-dark text-white text-center py-3">
                        <h3 class="mb-0">HighResAudio Downloader</h3>
                        <small class="text-muted">Descarga música en alta resolución con metadatos e imágenes</small>
                    </div>
                    <div class="card-body p-4">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                          {% if messages %}
                            {% for category, message in messages %}
                              <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                              </div>
                            {% for message in messages %}
                          {% endif %}
                        {% endwith %}

                        <form method="POST" action="/download">
                            <div class="mb-3">
                                <label for="url" class="form-label font-weight-bold">Enlace del Álbum o Pista de HighResAudio:</label>
                                <input type="url" class="form-control" id="url" name="url" required 
                                       placeholder="https://www.highresaudio.com/es/album/artist/name-album">
                                <div class="form-text">Asegúrate de que tu cuenta de HighResAudio posea permisos activos para la descarga.</div>
                            </div>
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary btn-lg">Iniciar Descarga</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
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
        flash("Por favor, introduce un enlace válido.", "error")
        return redirect(url_for("index"))

    try:
        # Nota: El script HRA-DL original utiliza un archivo de configuración o variables de entorno.
        # Aquí ejecutamos el script nativo mediante subprocess pasándole la URL como argumento.
        # Asegúrate de que HRA-DL.py admita recibir la URL por argumento (ej. `python HRA-DL.py --url <URL>`)
        # o en su defecto, modifica el script principal para aceptar el parámetro.
        
        process = subprocess.run(
            ["python", "HRA-DL.py", "--url", song_url],
            capture_output=True,
            text=True,
            timeout=300 # Límite de tiempo de 5 minutos por descarga
        )

        if process.returncode == 0:
            flash("¡Descarga completada con éxito al 100% con metadatos e imágenes!", "success")
        else:
            error_message = process.stderr.strip() or "Error desconocido durante la ejecución del script."
            flash(f"Error en el proceso: {error_message}", "error")

    except subprocess.TimeoutExpired:
        flash("La descarga ha tardado demasiado tiempo y se ha interrumpido.", "error")
    except Exception as e:
        flash(f"Ocurrió un error inesperado en el servidor: {str(e)}", "error")

    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
