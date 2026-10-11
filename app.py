import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>HRA Downloader Web</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <h2 class="mb-4">HighResAudio Downloader Web</h2>
            <div class="card p-4 shadow-sm">
                <form action="/download" method="POST">
                    <div class="mb-3">
                        <label for="url" class="form-label">Enlace de la pista/álbum de HighResAudio:</label>
                        <input type="text" class="form-control" id="url" name="url" required placeholder="https://www.highresaudio.com/...">
                    </div>
                    <button type="submit" class="btn btn-primary">Iniciar Descarga con Metadatos</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/download', methods=['POST'])
def download():
    song_url = request.form.get('url')
    # Aquí se invoca de manera programática la lógica interna de HRA-DL.py
    # Ejemplo simulado de ejecución del proceso de descarga:
    try:
        # Nota: Asegúrate de adaptar esta llamada a la función principal expuesta por HRA-DL.py
        os.system(f"python HRA-DL.py --url '{song_url}'")
        return "<h3>¡Descarga completada con éxito! Revisa la carpeta de destino del servidor con sus metadatos e imágenes.</h3><a href='/'>Volver</a>"
    except Exception as e:
        return f"<h3>Ocurrió un error en la descarga: {e}</h3><a href='/'>Volver</a>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
