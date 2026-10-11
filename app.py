from flask import Flask, render_template, request, jsonify
# Aquí importarías o integrarías las funciones del script HRA-DL
# import hradl_script 

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/descargar', methods=['POST'])
def descargar():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        print(f"Iniciando descarga para el enlace: {url}")
        
        # --- AQUÍ LLAMAS AL SCRIPT DE HRA-DL ---
        # Ejemplo: hradl_script.download(url)
        # ---------------------------------------
        
        return jsonify({'success': True, 'message': 'Descarga completada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
