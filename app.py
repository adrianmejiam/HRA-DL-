import os
import getpass

def mostrar_menu():
    os.system('clear')
    print("==================================")
    print("   HRA-DL ANDROID SIMPLE APP     ")
    print("==================================")
    print("1. Configurar credenciales (Email/Password)")
    print("2. Descargar álbum / pista")
    print("3. Salir")
    print("==================================")

while True:
    mostrar_menu()
    opcion = input("Selecciona una opción: ").strip()

    if opcion == "1":
        email = input("Introduce tu correo de HighResAudio: ")
        password = getpass.getpass("Introduce tu contraseña: ")
        # Guardar en un archivo de configuración básico
        with open("config.txt", "w") as f:
            f.write(f"{email}\n{password}")
        print("\n¡Credenciales guardadas con éxito!")
        input("\nPresiona Enter para continuar...")

    elif opcion == "2":
        if not os.path.exists("config.txt"):
            print("\n[!] Primero debes configurar tus credenciales (Opción>
            input("\nPresiona Enter para continuar...")
            continue

        url = input("Introduce el enlace (URL) del álbum en highresaudio.c>
        if url:
            print("\nIniciando descarga...")
            # Aquí puedes mandar a llamar la lógica de HRA-DL.py adaptada
            os.system(f"python HRA-DL.py '{url}'")
        else:
            print("\n[!] La URL no puede estar vacía.")
        input("\nPresiona Enter para continuar...")

    elif opcion == "3":
        print("\n¡Hasta luego!")
        break
    else:
        print("\n[!] Opción no válida.")
        input("\nPresiona Enter para continuar...")
