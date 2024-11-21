import socket
import threading
import random

# Daftar tema dan kata-kata
themes = {
    "makanan": ["nasi goreng", "rendang", "sate", "bakso"],
    "olahraga": ["sepak bola", "basket", "renang", "bulu tangkis"],
    "hewan": ["kucing", "anjing", "gajah", "singa"],
    "buah": ["apel", "pisang", "jeruk", "mangga"]
}

# Variabel global
current_theme = None
current_word = None
clue = None
clients = []
scores = {}
round_number = 1
max_rounds = 5
is_waiting_for_continue = False
lock = threading.Lock()  # Lock untuk sinkronisasi thread

# Fungsi untuk menangani client
def handle_client(client_socket, addr):
    global round_number, is_waiting_for_continue

    print(f"Koneksi baru dari {addr}")
    try:
        # Terima nama pemain
        client_name = client_socket.recv(1024).decode("utf-8").strip()
        print(f"Pemain {client_name} bergabung!")
        scores[client_name] = 0
        clients.append((client_socket, client_name))

        # Kirim petunjuk awal
        client_socket.send(clue.encode("utf-8"))

        while True:
            # Terima pesan dari client
            message = client_socket.recv(1024).decode("utf-8").strip()
            print(f"Pesan diterima dari {client_name}: {message}")

            if message == "!points":
                # Kirim skor ke client
                points_message = f"Poin Anda: {scores[client_name]}"
                client_socket.send(points_message.encode("utf-8"))
            elif message == "!scoreboard":
                # Kirim leaderboard/scoreboard ke client
                send_scoreboard(client_socket)
            elif is_waiting_for_continue and message == "!continue":
                # Pemain memilih untuk melanjutkan ronde
                with lock:
                    if round_number >= max_rounds:
                        round_number = 1  # Reset ronde ke awal
                        broadcast("Memulai ronde baru! Skor tetap dipertahankan.")
                    is_waiting_for_continue = False
                broadcast(f"{client_name} memilih untuk melanjutkan! Ronde {round_number} dimulai.")
                new_round()
            elif message.lower() == current_word.lower() and not is_waiting_for_continue:
                # Jika pemain menjawab benar
                with lock:
                    scores[client_name] += 3 if round_number <= max_rounds else 2
                broadcast(f"{client_name} menjawab dengan benar! Ronde selesai.")
                with lock:
                    if round_number >= max_rounds:
                        is_waiting_for_continue = True
                        broadcast("Ronde terakhir selesai! Ketik '!continue' untuk memulai ronde baru atau '!points' untuk cek skor.")
                    else:
                        round_number += 1
                        new_round()
            else:
                # Jawaban salah
                client_socket.send("Jawaban salah! Coba lagi.".encode("utf-8"))
    except Exception as e:
        print(f"Koneksi terputus dari {addr} dengan error: {e}")
    finally:
        # Hapus client dari daftar jika terputus
        with lock:
            clients.remove((client_socket, client_name))
        client_socket.close()
        print(f"{client_name} telah terputus dari server.")

# Fungsi untuk mengirim pesan ke semua client
def broadcast(message):
    for client, _ in clients:
        try:
            client.send(message.encode("utf-8"))
        except:
            pass

# Fungsi untuk mengirim scoreboard ke semua client
def send_scoreboard(client_socket=None):
    scoreboard = "\nScoreboard:\n"
    for name, score in scores.items():
        scoreboard += f"{name}: {score} poin\n"
    
    # Kirim ke semua client
    if client_socket:
        client_socket.send(scoreboard.encode("utf-8"))
    else:
        for client, _ in clients:
            try:
                client.send(scoreboard.encode("utf-8"))
            except:
                pass

# Memulai ronde baru
def new_round():
    global current_theme, current_word, clue
    current_theme = random.choice(list(themes.keys()))
    current_word = random.choice(themes[current_theme])
    clue = f"Temanya adalah '{current_theme}'. Kata terdiri dari {len(current_word)} huruf."
    broadcast(clue)

    # Kirim scoreboard setelah ronde selesai
    send_scoreboard()

# Fungsi utama server
def start_server():
    global round_number
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(5)
    print("Server berjalan di port 5555 dan menunggu koneksi...")

    # Mulai ronde pertama
    new_round()

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()

if __name__ == "__main__":
    start_server()
