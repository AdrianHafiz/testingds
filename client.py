import socket
import threading

# Fungsi untuk menerima pesan dari server
def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode("utf-8")
            print(message)
        except:
            print("Koneksi terputus dari server.")
            break

# Fungsi utama client
def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(("127.0.0.1", 5555))
        print("Terhubung ke server!")
    except Exception as e:
        print(f"Gagal terhubung ke server: {e}")
        return

    name = input("Masukkan nama Anda: ")
    client.send(name.encode("utf-8"))

    # Thread untuk menerima pesan dari server
    threading.Thread(target=receive_messages, args=(client,)).start()

    while True:
        message = input()
        if message:
            client.send(message.encode("utf-8"))

if __name__ == "__main__":
    start_client()
