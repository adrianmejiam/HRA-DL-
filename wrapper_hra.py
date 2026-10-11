import argparse
import sys

def main():
    # 1. Configurar el analizador de argumentos
    parser = argparse.ArgumentParser(description="HRA-DL Configurable Wrapper")
    
    parser.add_argument('--email', type=str, required=True, help='Correo electrónico de HighResAudio')
    parser.add_argument('--password', type=str, required=True, help='Contraseña de HighResAudio')
    parser.add_argument('--quality', type=str, default='flac-hi-res', 
                        choices=['flac-hi-res', 'flac-cd', 'mp3'], 
                        help='Calidad de audio deseada')
    parser.add_argument('--path', type=str, default='./downloads', 
                        help='Carpeta de destino para las descargas')
    
    # Opciones avanzadas adicionales
    parser.add_argument('--cover', action='store_true', help='Descargar carátula del álbum')
    parser.add_argument('--skip-existing', action='store_true', help='Saltar archivos ya descargados')

    args = parser.parse_args()

    # 2. Mostrar la configuración recibida (para depuración)
    print("--- Iniciando descarga con configuración personalizada ---")
    print(f"Usuario: {args.email}")
    print(f"Calidad seleccionada: {args.quality}")
    print(f"Ruta de destino: {args.path}")
    print(f"Descargar carátula: {args.cover}")
    
    # 3. Aquí integras la lógica original del script de descarga
    # Ejemplo: iniciar_descarga(args.email, args.password, args.quality, args.path)

if __name__ == '__main__':
    main()
