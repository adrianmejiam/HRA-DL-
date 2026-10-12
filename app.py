import os
import shutil
import subprocess
import time
import threading
from flask import Flask, render_template, request, jsonify, send_file, Response, after_this_request

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave-secreta-por-defecto")

download_logs = {}
session_metadata = {}

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

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=download_dir,
            env=env
        )

        for line in process.stdout:
            clean_line = line.strip()
            if clean_line:
                download_logs[session_id].append(clean_line)
                session_metadata[session_id]["last_log"] = clean_line

        process.wait()

        if process.returncode != 0:
            error_msg = f"[ERROR] El script HRA-DL.py finalizó con código de salida {process.returncode}."
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
        
        download_logs[session_id].append("[DONE]")
        session_metadata[session_id]["status"] = "Completado"
        session_metadata[session_id]["last_log"] = "Descarga e inicio de sesión finalizados con éxito."
        session_metadata[session_id]["ready_to_download"] = True

    except Exception as e:
        err_str = f"[ERROR] Ocurrió un error inesperado: {str(e)}"
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

    session_id = str(time.time_ns())
    
    thread = threading.Thread(target=run_download_process, args=(session_id, song_url, email, password, cookie_data))
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "session_id": session_id})

@app.route("/api/sessions")
def get_sessions():
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
    download_dir = os.path.join(os.getcwd(), f"downloads_{session_id}")
    
    if os.path.exists(zip_filename):
        @after_this_request
        def cleanup_session_files(response):
            try:
                if os.path.exists(zip_filename):
                    os.remove(zip_filename)
                if os.path.exists(download_dir):
                    shutil.rmtree(download_dir, ignore_errors=True)
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
