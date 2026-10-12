import os
import shutil
import subprocess
import time
import threading
from flask import Flask, render_template_string, request, jsonify, send_file, Response, after_this_request

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave-secreta-por-defecto")

download_logs = {}
session_metadata = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HIGHRESAUDIO - Descargador Lossless</title>
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
            height: 200px;
            overflow-y: auto;
            border-radius: 6px;
            padding: 10px;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
            white-space: pre-wrap;
            word-break: break-all;
        }
    </style>
</head>
<body class="bg-light d-flex flex-column min-vh-100">
    <div class="container py-5 my-auto">
        <div class="row justify-content-center">
            <div class="col-md-10">
                <ul class="nav nav-tabs mb-4 justify-content-center fw-bold" id="mainTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active text-dark" id="download-tab" data-bs-toggle="tab" data-bs-target="#download-pane" type="button" role="tab">Nueva Descarga</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link text-dark" id="monitor-tab" data-bs-toggle="tab" data-bs-target="#monitor-pane" type="button" role="tab" onclick="refreshActiveDownloads()">Panel de Avance y Descargas</button>
                    </li>
                </ul>

                <div class="tab-content" id="mainTabsContent">
                    <!-- PESTAÑA 1: NUEVA DESCARGA -->
                    <div class="tab-pane fade show active" id="download-pane" role="tabpanel">
                        <div class="card shadow-lg border-0">
                            <div class="card-header brand-header text-white text-center py-4">
                                <div class="d-flex align-items-center justify-content-center">
                                    <img src="https://thumb.wikimedia.org/wikipedia/en/thumb/d/d1/Hi-Res_Audio_%28logo%29.svg/1280px-Hi-Res_Audio_%28logo%29.svg.png" 
                                         alt="Hi-Res Audio Logo" class="hires-logo">
                                    <h2 class="mb-0 fw-bold tracking-wide text-warning">HIGHRESAUDIO</h2>
                                </div>
                                <p class="text-light small mt-2 mb-0 opacity-75">Descarga Directa Lossless en Máxima Fidelidad (Sin Pérdida)</p>
                            </div>
                            <div class="card-body p-4">
                                <div id="alert-container"></div>

                                <form id="download-form">
                                    <div class="mb-3">
                                        <label for="url" class="form-label fw-bold">Enlace del Álbum o Pista de HIGHRESAUDIO.com:</label>
                                        <input type="url" class="form-control form-control-lg" id="url" name="url" required 
                                               placeholder="https://www.highresaudio.com/es/album/artist/name-album">
                                    </div>

                                    <div class="card bg-light border mb-3">
                                        <div class="card-body p-3">
                                            <h6 class="fw-bold text-dark mb-2">Autenticación de Cuenta HIGHRESAUDIO (Opcional):</h6>
                                            <div class="row g-2">
                                                <div class="col-md-6">
                                                    <label for="email" class="form-label small fw-bold text-muted mb-1">Correo Electrónico:</label>
                                                    <input type="email" class="form-control form-control-sm" id="email" name="email" 
                                                           placeholder="usuario@ejemplo.com">
                                                </div>
                                                <div class="col-md-6">
                                                    <label for="password" class="form-label small fw-bold text-muted mb-1">Contraseña:</label>
                                                    <input type="password" class="form-control form-control-sm" id="password" name="password" 
                                                           placeholder="••••••••">
                                                </div>
                                            </div>
                                            <div class="mt-2">
                                                <label for="cookie" class="form-label small fw-bold text-muted mb-1">O usar Cookie / Token de Sesión directo:</label>
                                                <input type="text" class="form-control form-control-sm" id="cookie" name="cookie" 
                                                       placeholder="Pega tu cookie de sesión si prefieres no ingresar tus credenciales">
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div id="info-panel" class="alert alert-secondary d-none mb-3">
                                        <ul class="mb-0 small">
                                            <li><strong>Tamaño estimado:</strong> <span id="est-size">Calculando...</span></li>
                                            <li><strong>Tiempo estimado de espera:</strong> <span id="est-time">Calculando...</span></li>
                                        </ul>
                                    </div>

                                    <!-- CUADRO DE AVANCE / CONSOLA EN TIEMPO REAL -->
                                    <div id="progress-container" class="mb-3 d-none">
                                        <label class="text-primary fw-bold mb-1">Consola de Avance en Tiempo Real:</label>
                                        <div id="console-output" class="console-box mb-2">Inicializando proceso de descarga...</div>
                                        <div class="progress" style="height: 15px;">
                                            <div class="progress-bar progress-bar-striped progress-bar-animated bg-warning" 
                                                 role="progressbar" style="width: 100%;" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"></div>
                                        </div>
                                    </div>

                                    <div class="d-grid" id="btn-container">
                                        <button type="submit" id="submit-btn" class="btn btn-warning btn-lg fw-bold text-dark shadow-sm">Iniciar Descarga en Máxima Fidelidad</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>

                    <!-- PESTAÑA 2: PANEL DE AVANCE Y DESCARGAS -->
                    <div class="tab-pane fade" id="monitor-pane" role="tabpanel">
                        <div class="card shadow-lg border-0">
                            <div class="card-header bg-dark text-white py-3 d-flex justify-content-between align-items-center">
                                <h5 class="mb-0 text-warning fw-bold">Panel de Monitoreo de Descargas Activas</h5>
                                <button class="btn btn-sm btn-outline-light" onclick="refreshActiveDownloads()">Actualizar Lista</button>
                            </div>
                            <div class="card-body p-4">
                                <div id="active-downloads-list">
                                    <p class="text-muted text-center">Cargando sesiones activas...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="text-center mt-4 text-muted small">
                    Desarrollado por <strong>adrianmejiam</strong> | &copy; 2026
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('url').addEventListener('input', function(e) {
            const val = e.target.value;
            const infoPanel = document.getElementById('info-panel');
            if (val.includes('album')) {
                document.getElementById('est-size').textContent = 'Aprox. 350 MB - 1.5 GB (FLAC Lossless)';
                document.
