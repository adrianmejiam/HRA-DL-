import os
import shutil
import subprocess
import time
import threading
import json
import requests
from flask import Flask, render_template, request, jsonify, send_file, Response, after_this_request

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave-secreta-por-defecto")

download_logs = {}
session_metadata = {}
data_lock = threading.Lock()

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
    return render_template("index.html")

def verify_hra_credentials(email, password):
    try:
        url = f"https://streaming.highresaudio.com:8182/vault3/user/login?password={password}&username={email}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "has_subscription" in data:
                return True, "Credenciales verificadas con éxito."
        return False, "Credenciales inválidas o la cuenta no cuenta con suscripción activa."
    except Exception as e:
        return False, f"Error al conectar con el servidor de autenticación: {str(e)}"

def run_download_process(session_id, song_url, email, password, cookie_data):
    with data_lock:
        download_logs[session_id] = []
        session_metadata[session_id] = {
            "url": song_url,
            "status": "Procesando...",
            "last_log": "Iniciando proceso de descarga lossless...",
            "ready_to_download": False
        }
    
    download_dir = os.path.join(os.getcwd(), f"downloads_{session_id}")
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, "HRA-DL.py")

        config_data = {
            "email": email if email else "usuario_invitado@ejemplo.com",
            "password": password if password else "password_dummy"
        }
        
        config_file_path = os.path.join(download_dir, "config.json")
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        if cookie_data:
            cookie_file_path = os.path.join(download_dir, "cookies.txt")
            with open(cookie_file_path, "w", encoding="utf-8") as f:
                f.write(cookie_data)

        cmd = ["python3", script_path, "--url", song_url]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=download_dir
        )

        for line in process.stdout:
            clean_line = line.strip()
            if clean_line:
                with data_lock:
                    download_logs[session_id].append(clean_line)
                    session_metadata[session_id]["last_log"] = clean_line

        process.wait()

        if process.returncode != 0:
            error_msg = f"[ERROR] HRA-DL.py finalizó con código de salida {process.returncode}."
            with data_lock:
                download_logs[session_id].append(error_msg)
                session_metadata[session_id]["status"] = "Error"
                session_metadata[session_id]["last_log"] = error_msg
            return

        allowed_extensions = ('.flac', '.jpg', '.jpeg', '.png')
        for root, dirs, files in os.walk(download_dir):
            for file in files:
                if not file.lower().endswith(allowed_extensions):
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception:
                        pass

        current_time = time.time()
        for root, dirs, files in os.walk(download_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.utime(file_path, (current_time, current_time))
                except Exception:
                    pass

        zip_path = os.path.join(os.getcwd(), f"HRA_Download_{session_id}")
        shutil.make_archive(zip_path, 'zip', download_dir)
        
        with data_lock:
            download_logs[session_id].append("[DONE]")
            session_metadata[session_id]["status"] = "Completado"
            session_metadata[session_id]["last_log"] = "Descarga Lossless finalizada con éxito."
            session_metadata[session_id]["ready_to_download"] = True

    except Exception as e:
        err_str = f"[ERROR] Ocurrió un error inesperado en el servidor: {str(e)}"
        with data_lock:
            download_logs[session_id].append(err_str)
            session_metadata[session_id]["status"] = "Error"
            session_metadata[session_id]["last_log"] = err_str

@app.route("/start-download", methods=["POST"])
def start_download():
    song_url = request.form.get("url")
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    cookie_data = request.form.get("cookie", "")
    
    if not song_url:
        return jsonify({"success": False, "message": "Por favor, introduce un enlace válido."}), 400

    if email and password:
        is_valid, msg = verify_hra_credentials(email, password)
        if not is_valid:
            return jsonify({"success": False, "message": f"Autenticación fallida: {msg}"}), 400

    session_id = str(time.time_ns())
    
    thread = threading.Thread(target=run_download_process, args=(session_id, song_url, email, password, cookie_data))
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "session_id": session_id})

@app.route("/api/sessions")
def get_sessions():
    with data_lock:
        sessions_list = []
        for sid, meta in session_metadata.items():
            zip_exists = os.path.exists(f"HRA_Download_{sid}.zip")
            sessions_list.append({
                "session_id": sid,
                "url": meta["url"],
                "status": meta["status"],
                "last_log": meta["last_log"],
                "ready_to_download": meta["ready_to_download"] and zip_exists
            })
        sessions_list.reverse()
    return jsonify({"sessions": sessions_list})

@app.route("/stream-logs/<session_id>")
def stream_logs(session_id):
    def generate():
        index = 0
        while True:
            with data_lock:
                logs = list(download_logs.get(session_id, []))
            
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
    download_dir = os.path.join(os.getcwd(), f"downloads_{session_id}")
    
    if os.path.exists(zip_filename):
        @after_this_request
        def cleanup_session_files(response):
            try:
                if os.path.exists(zip_filename):
                    os.remove(zip_filename)
                if os.path.exists(download_dir):
                    shutil.rmtree(download_dir, ignore_errors=True)
                with data_lock:
                    if session_id in download_logs:
                        del download_logs[session_id]
                    if session_id in session_metadata:
                        del session_metadata[session_id]
            except Exception as e:
                print(f"Error al limpiar recursos de sesión {session_id}: {e}")
            return response

        return send_file(zip_filename, as_attachment=True, download_name="Album_HiRes_Lossless.zip")
        
    return jsonify({"success": False, "message": "Archivo ZIP no encontrado."}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
