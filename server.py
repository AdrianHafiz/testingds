import socket
import threading
import random

# Daftar tema dan kata-kata
themes = {
    "makanan": ["nasi goreng", "rendang", "sate", "bakso", "gudeg", "pecel", "soto", "gulai", "pindang"],
    "olahraga": ["sepak bola", "basket", "renang", "bulu tangkis", "voli", "futsal", "tenis meja", "panjat tebing"],
    "hewan": ["kucing", "anjing", "gajah", "singa", "harimau", "zebra", "panda", "koala", "kuda", "beruang"],
    "buah": ["apel", "pisang", "jeruk", "mangga", "stroberi", "melon", "anggur", "alpukat", "rambutan", "durian"]
}

# Variabel global
current_theme = None
current_word = None
revealed_indices = []
clients = []
scores = {}
clues_used = {}
max_rounds = 5
round_number = 1
current_turn = 0
lock = threading.Lock()
condition = threading.Condition(lock)
game_active = True
game_started = False
start_count = 0  # Menambahkan variabel untuk menghitung pemain yang sudah mengetik '!start'

# Fungsi untuk menangani client
def handle_client(client_socket, addr):
    global round_number, current_word, current_theme, current_turn, game_active, max_rounds, game_started, start_count

    try:
        # Terima nama pemain
        client_name = client_socket.recv(1024).decode("utf-8").strip()
        print(f"[INFO] Pemain '{client_name}' bergabung dari {addr}!")
        scores[client_name] = 0
        clues_used[client_name] = 0
        with lock:
            clients.append((client_socket, client_name))

        # Kirim pesan selamat datang
        client_socket.send("\nSelamat datang di permainan tebak kata!\n".encode("utf-8"))
        client_socket.send("\nKetik '!start' untuk memulai permainan setelah semua pemain siap.\n".encode("utf-8"))

        while not game_started:
            message = client_socket.recv(1024).decode("utf-8").strip()
            if message.lower() == "!start":
                with lock:
                    start_count += 1
                    client_socket.send("\nMenunggu pemain lain untuk memulai permainan...\n".encode("utf-8"))
                    if start_count == len(clients):  # Jika semua pemain sudah siap
                        # Meminta pemain memilih jumlah ronde
                        client_socket.send("\nSilakan pilih jumlah ronde yang ingin dimainkan (misalnya: 3):\n".encode("utf-8"))
                        chosen_rounds = int(client_socket.recv(1024).decode("utf-8").strip())
                        max_rounds = chosen_rounds  # Set jumlah ronde yang dipilih oleh pemain
                        game_started = True
                        broadcast("\nSemua pemain siap! Permainan dimulai!\n")
                        broadcast(f"\nJumlah ronde yang dipilih: {max_rounds}\n")
                        # Kirim giliran pertama
                        broadcast(f"\nGiliran pertama: {clients[current_turn][1]}!\n")
                        break
                    else:
                        client_socket.send(f"\nTunggu {len(clients) - start_count} pemain lainnya untuk memulai.\n".encode("utf-8"))

        # Setelah game dimulai, pilih tema
        if game_started:
            current_theme = random.choice(list(themes.keys()))
            current_word = random.choice(themes[current_theme])
            print(f"[INFO] Tema yang dipilih: {current_theme}.")
            broadcast(f"\n[Tema yang dipilih: '{current_theme}']")  # Hanya menampilkan tema, bukan daftar kata-kata
            # Menampilkan tema dan instruksi ke semua pemain
            broadcast(f"\n[Tema: '{current_theme}'] Ketik jawaban atau '!clue' untuk petunjuk:\n")

        while game_active:
            with condition:
                while clients[current_turn][1] != client_name:
                    condition.wait()

                # Kirim pesan giliran ke pemain
                if clients[current_turn][1] == client_name:
                    client_socket.send("\n[INFO] Sekarang giliran Anda!\n".encode("utf-8"))

                # Kirim tema dan instruksi ke pemain yang sedang giliran
                client_socket.send(f"\n[Tema: '{current_theme}'] Ketik jawaban atau '!clue' untuk petunjuk:\n".encode("utf-8"))
                message = client_socket.recv(1024).decode("utf-8").strip()

                if message.lower() == "!clue":
                    if clues_used[client_name] < 2:
                        reveal_clue(client_socket)
                        clues_used[client_name] += 1
                    else:
                        client_socket.send("\n[INFO] Anda sudah menggunakan semua clue pada ronde ini!\n".encode("utf-8"))
                elif message.lower() == current_word.lower():
                    scores[client_name] += 3
                    print(f"[INFO] {client_name} menjawab benar! Kata adalah '{current_word}'.")
                    next_round()
                else:
                    client_socket.send("\n[INFO] Jawaban salah! Tunggu giliran berikutnya.\n".encode("utf-8"))

                # Pindahkan giliran ke pemain berikutnya (pastikan berurutan)
                current_turn = (current_turn + 1) % len(clients)
                print(f"[INFO] Giliran berikutnya: {clients[current_turn][1]}")
                broadcast(f"\nGiliran berikutnya: {clients[current_turn][1]}.\n")
                condition.notify_all()

    except Exception as e:
        print(f"[ERROR] Koneksi terputus dari {addr} dengan error: {e}")
    finally:
        with lock:
            clients.remove((client_socket, client_name))
        client_socket.close()
        print(f"[INFO] Pemain '{client_name}' telah terputus dari server.")


# Fungsi untuk memberikan clue
def reveal_clue(client_socket):
    global revealed_indices
    while True:
        random_index = random.randint(0, len(current_word) - 1)
        if random_index not in revealed_indices:
            revealed_indices.append(random_index)
            break
    revealed_word = "".join(
        current_word[i] if i in revealed_indices else "_" for i in range(len(current_word))
    )
    clue_message = f"\n[Clue] Kata: {revealed_word} ({len(current_word)} huruf).\n"
    client_socket.send(clue_message.encode("utf-8"))

# Fungsi untuk memulai ronde baru
def next_round():
    global round_number, current_theme, current_word, revealed_indices, clues_used, current_turn, game_active

    if round_number >= max_rounds:
        print("\n[INFO] Permainan selesai! Berikut adalah skor akhir: ")
        send_scoreboard()
        broadcast("\nPermainan selesai! Ketik '!continue' untuk melanjutkan atau '!end' untuk mengakhiri permainan.\n")
        decision = wait_for_decision()
        if decision == "!continue":
            start_new_game()
        elif decision == "!end":
            broadcast("\n[INFO] Berikut adalah skor akhir permainan:\n")
            send_scoreboard()
            broadcast("\nTerima kasih telah bermain! Permainan akan segera ditutup.\n")
            game_active = False
        return

    round_number += 1
    current_theme = random.choice(list(themes.keys()))
    current_word = random.choice(themes[current_theme])
    revealed_indices = []
    clues_used = {client[1]: 0 for client in clients}
    current_turn = 0  # Pastikan giliran dimulai dari pemain pertama
    broadcast(f"\n--- Ronde {round_number} ---")
    print(f"[INFO] Tema baru: '{current_theme}'.")

# Fungsi untuk memulai permainan baru
def start_new_game():
    global round_number, max_rounds, revealed_indices, clues_used, current_turn

    broadcast("\nPermainan baru dimulai! Ketik jumlah ronde yang baru:\n")
    max_rounds = int(clients[0][0].recv(1024).decode("utf-8").strip())
    round_number = 1
    revealed_indices = []
    clues_used = {client[1]: 0 for client in clients}
    current_turn = 0
    print(f"[INFO] Permainan baru dimulai dengan {max_rounds} ronde.")

# Fungsi untuk menunggu keputusan semua pemain
def wait_for_decision():
    decisions = []
    for client, name in clients:
        client.send("\nKetik '!continue' untuk melanjutkan atau '!end' untuk mengakhiri permainan:\n".encode("utf-8"))
        decision = client.recv(1024).decode("utf-8").strip().lower()
        decisions.append(decision)

    # Jika semua pemain memilih sama, lanjutkan atau akhiri
    if all(dec == "!continue" for dec in decisions):
        return "!continue"
    return "!end"

# Fungsi untuk mengirim pesan ke semua client
def broadcast(message):
    for client, _ in clients:
        try:
            client.send(message.encode("utf-8"))
        except:
            pass

# Fungsi untuk mengirim scoreboard ke semua client
def send_scoreboard():
    scoreboard = "\n[Scoreboard]\n"
    for name, score in scores.items():
        scoreboard += f"{name}: {score} poin\n"
    broadcast(scoreboard)

# Fungsi utama server
def start_server():
    global current_theme, current_word

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(5)
    print("[INFO] Server berjalan di port 5555 dan menunggu koneksi...")

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()

if __name__ == "__main__":
    start_server()
