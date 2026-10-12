#!/usr/bin/env python3

# Standard
import os
import re
import sys
import json
import time
import platform
import traceback
import argparse
import subprocess

# Configuración de argumentos de línea de comandos
parser = argparse.ArgumentParser(description="HRA-DL Automatizado")
parser.add_argument("--url", type=str, help="URL de la pista o álbum en HighResAudio")
args = parser.parse_args()

# Third party
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

# ==========================================
# 🔧 RUTA DE DESCARGA (Termux)
# ==========================================
BASE_DOWNLOAD_PATH = "downloads"
# ==========================================

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0"
})

def getOs():
    return platform.system() == 'Windows'

def osCommands(x):
    if getOs():
        if x == "p":
            os.system('pause >nul')
        elif x == "c":
            os.system('cls')
        elif x == "t":
            os.system('title HRA-DL (Optimized)')
    else:
        if x == "p":
            os.system("read -rsp $''")  # Pausa segura para entornos Unix
        elif x == "c":
            os.system('clear')
        elif x == "t":
            sys.stdout.write("\x1b]2;HRA-DL (Optimized)\x07")

def login(email, pwd):
    url = f'https://streaming.highresaudio.com:8182/vault3/user/login?password={pwd}&username={email}'
    try:
        r = session.get(url, timeout=15)
        
        # Intentar parsear el JSON de respuesta incluso si el código no es 200
        try:
            data = r.json()
        except Exception:
            data = {"raw_text": r.text}

        if r.status_code == 200 and "has_subscription" in data:
            print("Signed in successfully.\n")
            return r.text
        else:
            print(f"\n[ERROR DE LOGIN] Código HTTP: {r.status_code}")
            print(f"Respuesta del servidor: {json.dumps(data, indent=2, ensure_ascii=False)}")
            osCommands('p')
            sys.exit()
            
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR DE RED] No se pudo conectar al servidor de autenticación: {e}")
        osCommands('p')
        sys.exit()

def fetchMetadata(albumId, userData):
    url = f'https://streaming.highresaudio.com:8182/vault3/vault/album/?album_id={albumId}&userData={userData}'
    try:
        r = session.get(url, timeout=15)
        
        # Intentar extraer la respuesta en JSON para diagnóstico
        try:
            data = r.json()
        except Exception:
            data = {"raw_text": r.text}

        if r.status_code != 200:
            print(f"\n[ERROR DE METADATA] El servidor respondió con el código HTTP {r.status_code}")
            print(f"URL consultada: {url}")
            print(f"Detalle del servidor: {json.dumps(data, indent=2, ensure_ascii=False)}")
            osCommands('p')
            sys.exit()
            
        # Verificar si la estructura interna del JSON contiene los resultados esperados
        if 'data' not in data or 'results' not in data['data']:
            print(f"\n[ERROR DE METADATA] La estructura de la respuesta JSON es inesperada:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            osCommands('p')
            sys.exit()
            
        return data

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR DE RED] Fallo al solicitar metadatos del álbum: {e}")
        osCommands('p')
        sys.exit()

def dirSetup(path):
    os.makedirs(path, exist_ok=True)
    return path

def fileSetup(fname):
    if os.path.isfile(fname):
        os.remove(fname)

# ==========================================
# 📄 TRACKLIST GENERATOR
# ==========================================
def save_tracklist(tracks, albumPath):
    tracklist_path = os.path.join(albumPath, "Tracklist.txt")
    with open(tracklist_path, "w", encoding="utf-8") as f:
        f.write("Tracklist:\n")
        for i, track in enumerate(tracks, start=1):
            number = f"{i:02d}"
            title = track.get("title", "Unknown Title")
            f.write(f"{number} {title}\n")

# ==========================================
# 🔥 FETCH TRACK CON ANTI-CONGELAMIENTO
# ==========================================
def fetchTrack(albumId, fname, spec, trackNum, trackTitle, trackTotal, url):
    max_retries = 6
    timeout_seconds = 8
    attempt = 0

    while attempt < max_retries:
        try:
            session.headers.update({
                "range": "bytes=0-",
                "referer": f"https://stream-app.highresaudio.com/album/{albumId}"
            })

            print(f"Downloading {trackNum}/{trackTotal}: {trackTitle} - {spec} (Attempt {attempt+1})")

            r = session.get(url, stream=True, timeout=15)
            size = int(r.headers.get('content-length', 0))

            downloaded = 0
            last_progress_time = time.time()

            with open(fname, 'wb') as f:
                with tqdm(total=size, unit='B', unit_scale=True, unit_divisor=1024) as bar:
                    for chunk in r.iter_content(128 * 1024):
                        if chunk:
                            f.write(chunk)
                            chunk_size = len(chunk)
                            downloaded += chunk_size
                            bar.update(chunk_size)
                            last_progress_time = time.time()

                        if time.time() - last_progress_time > timeout_seconds:
                            raise Exception("Download stalled")

            return  # Success

        except Exception:
            attempt += 1
            print(f"\n⚠ Download interrupted. Retrying... ({attempt}/{max_retries})\n")
            time.sleep(2)

    print(f"\n❌ Failed after {max_retries} attempts.\n")

def fetchFile(url, dest):
    fileSetup(dest)
    r = session.get(url, stream=True)
    size = int(r.headers.get('content-length', 0))

    with open(dest, 'wb') as f:
        with tqdm(total=size, unit='B', unit_scale=True, unit_divisor=1024) as bar:
            for chunk in r.iter_content(128 * 1024):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

def sanitizeFname(fname):
    if getOs():
        return re.sub(r'[\\/:*?"><|]', '-', fname)
    else:
        return re.sub('/', '-', fname)

def main(userData):
    
    if args.url:
        url = args.url.strip()
    else:
        url = input("Input HIGHRESAUDIO Store URL: ").strip()

    if not url:
        osCommands('c')
        return

    if not re.match(r"https?://(?:www\.)?highresaudio\.com/", url):
        print("Invalid URL.")
        time.sleep(1)
        osCommands('c')
        return

    osCommands('c')

    albumId = fetchAlbumId(url)
    metadata = fetchMetadata(albumId, userData)

    artist = metadata['data']['results']['artist']
    title = metadata['data']['results']['title']
    tracks = metadata['data']['results']['tracks']

    # ==========================================
    # 🔎 DETECTAR CALIDAD (Sample Rates)
    # ==========================================
    sample_rates = set()
    for t in tracks:
        try:
            rate = float(t['format'])
            sample_rates.add(rate)
        except:
            pass

    sample_rates = sorted(sample_rates)
    formatted_rates = [f"{r:.1f}kHz" if r % 1 == 0 else f"{r}kHz" for r in sample_rates]
    rate_string = " & ".join(formatted_rates)
    quality_tag = f"[HIGHRESAUDIO HRA 24bits/{rate_string}]"

    # ==========================================
    # 📘 DETECTAR BOOKLET
    # ==========================================
    hasBooklet = "booklet" in metadata['data']['results']
    if hasBooklet:
        albumFolder = f"{artist} - {title} {quality_tag} + Digital Booklet"
    else:
        albumFolder = f"{artist} - {title} {quality_tag}"

    print(f"{albumFolder}\n")

    albumPath = dirSetup(f"./{sanitizeFname(albumFolder)}")


    # Generar Tracklist
    save_tracklist(tracks, albumPath)

    # ==========================================
    # 🎨 COVER DOWNLOAD
    # ==========================================
    cover_data = metadata['data']['results'].get("cover")
    if cover_data:
        if "master" in cover_data and "file_url" in cover_data["master"]:
            print("Downloading Folder...")
            cover_url = "https://" + cover_data["master"]["file_url"]
            fetchFile(cover_url, os.path.join(albumPath, "Folder.jpg"))

    totalTracks = str(len(tracks)).zfill(2)

    for track in tracks:
        trackNum = str(track['trackNumber']).zfill(2)
        trackTitle = sanitizeFname(track['title'])

        tempFile = os.path.join(albumPath, f"{trackNum}.flac")
        finalFile = os.path.join(albumPath, f"{trackNum}. {trackTitle}.flac")

        fileSetup(tempFile)
        fileSetup(finalFile)

        fetchTrack(
            albumId,
            tempFile,
            f"{track['format']} kHz FLAC",
            trackNum,
            track['title'],
            totalTracks,
            track['url']
        )

        if os.path.exists(tempFile):
            os.rename(tempFile, finalFile)

    # ==========================================
    # 📘 BOOKLET DOWNLOAD
    # ==========================================
    if hasBooklet:
        print("Downloading Digital Booklet...")
        fetchFile(
            f"https://{metadata['data']['results']['booklet']}",
            os.path.join(albumPath, "booklet.pdf")
        )

    print("\nAlbum completed.")
    time.sleep(1)
    osCommands('c')

if __name__ == '__main__':
    osCommands('t')

    with open("config.json") as f:
        config = json.load(f)

    userData = login(config["email"], config["password"])

    try:
        while True:
            main(userData)
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
    except:
        traceback.print_exc()
        input("\nAn exception has occurred. Press enter to exit.")
        sys.exit()
