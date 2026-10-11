import os
import shutil
import tempfile
from flask import Flask, render_template, request, send_file, jsonify

app = Flask(__name__)

# NOTA: Asegúrate de importar las funciones reales de HRA-DL según el repositorio clonado.
# Por ejemplo, si el script principal tiene una función de descarga o un script ejecutable:
# from HRA_DL.hra import main_download_function as download_album

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_music():
    email = request.form.get('email')
    password = request.form.get('password')
    url = request.form.get('url')

    if not email or not password or not url:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    # Creamos un directorio temporal único para esta descarga
    temp_dir = tempfile.mkdtemp()
    
    try:
        # ==========================================
        # INTEGRACIÓN CON HRA-DL:
        # Aquí llamarías a la función del script original pasándole 
        # las credenciales, la URL y la ruta de salida (temp_dir).
        # Ejemplo:
        # download_album(email=email, password=password, url=url, output=temp_dir)
        # ==========================================

        # SIMULACIÓN DE DESCARGA (Eliminar esto al conectar la función real de HRA-DL)
        # Esto crea un archivo de prueba dentro del directorio temporal para verificar el ZIP
        dummy_file = os.path.join(temp_dir, "cancion_ejemplo_flac.flac")
        with open(dummy_file, "w") as f:
            f.write("Simulando contenido de audio en alta resolución...")

        # Comprimimos toda la carpeta de descargas en un archivo .zip
        zip_filename = "highresaudio_download"
        zip_path = shutil.make_archive(os.path.join(temp_dir, zip_filename), 'zip', temp_dir)

        # Enviamos el archivo ZIP generado directamente al navegador
        return send_file(
            zip_path,
            as_attachment=True,
            download_name="musica_hra.zip",
            mimetype="application/zip"
        )

    except Exception as e:
        # Limpieza en caso de error
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'error': f'Error durante la descarga: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
