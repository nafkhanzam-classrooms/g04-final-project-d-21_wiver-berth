[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/4SHtB1vz)

# Network Programming Final Project - WiverBerth

## Anggota Kelompok
| Nama           | NRP        | Kelas     |
| ---            | ---        | ----------|
| Willy Marcelius              | 5025241096           | Pemrograman Jaringan D          |
| Nathanael Oliver Amadhika Yuswana | 5025241109           | Pemrograman Jaringan D          |
| Rennard Filbert Tanjaya | 5025241122           | Pemrograman Jaringan D          |

## Link Youtube (Unlisted)
```
https://youtu.be/ZjdiS1pLYGk
```

## Penjelasan Program
Project ini adalah game **Pong Multiplayer berbasis jaringan** menggunakan Python, Pygame, dan socket UDP. Game berjalan dengan arsitektur **dedicated authoritative server**, sehingga posisi bola, skor, status room, dan hasil pertandingan dihitung oleh server lalu disinkronkan ke semua client. Client terdiri dari player dan spectator di room.

Client hanya mengirim input pemain seperti gerakan paddle, ping, create room, join room, quick match, surrender, dan exit room. Server kemudian mengirimkan state terbaru ke seluruh player dan spectator di room tersebut.

### Penjelasan Singkat File Program
- `client_gui.py` adalah program client yang menampilkan GUI game menggunakan Pygame. File ini menangani input user, menu utama, input username, create/join room, quick match, leaderboard, tampilan game, gerakan paddle, tombol surrender/leave, serta komunikasi UDP ke server.
- `server_engine.py` adalah program server utama yang menjalankan logika game secara authoritative. File ini mengatur pembuatan room, matchmaking, join room, spectator, validasi packet, posisi bola, skor, status pertandingan, reconnect handling, leaderboard, penyimpanan replay, dan pengiriman state game ke semua client.
- `network_config.py` berisi konfigurasi bersama yang digunakan oleh client dan server, seperti IP server, port, ukuran buffer, timeout client, ukuran layar, FPS, warna tampilan, serta fungsi `encode_packet()` dan `decode_packet()` untuk mengubah packet Python ke format JSON bytes dan sebaliknya.

## Alasan Menggunakan UDP
Game Pong membutuhkan update posisi secara real-time. UDP dipilih karena:
- Latency lebih rendah dibanding TCP karena tidak menunggu mekanisme retransmission dan ordering bawaan.
- Kehilangan satu paket posisi tidak fatal, karena server akan mengirim state terbaru lagi pada tick berikutnya.
- Cocok untuk sinkronisasi state game yang terus berubah cepat seperti posisi bola dan paddle.

Reliabilitas untuk event penting seperti join room, leaderboard, dan surrender tetap ditangani di level aplikasi dengan packet type yang eksplisit dan state server yang authoritative.

## Fitur Utama
- Real-time update menggunakan tick server 60 FPS.
- Game state synchronization lewat packet `STATE` dari server ke client.
- Room system: satu room berisi 2 player aktif, player tambahan otomatis menjadi spectator.
- Manual room: player dapat membuat room dan membagikan kode 5 digit.
- Matchmaking otomatis: tombol **Quick Match** mencari room kosong, atau membuat room baru jika belum ada lawan.
- Reconnect handling: jika player terputus, room masuk status `PAUSED` dan dapat dilanjutkan saat player reconnect memakai username yang sama.
- Ping/latency indicator di pojok kiri atas client.
- Logging aktivitas player di server.
- Anti-invalid packet sederhana melalui validasi packet type, username, room code, dan range gerakan paddle.

## Fitur Bonus
- Dedicated game server terpisah dari client.
- Spectator mode untuk user ke-3 dan seterusnya.
- Ranking system melalui leaderboard.
- Persistent leaderboard di file `leaderboard.json`.
- Match replay sederhana di folder `replays/` dalam format JSON saat match selesai.

## Cara Menjalankan
1. Jalankan server:
```bash
python server_engine.py
```

2. Jalankan minimal dua client di terminal berbeda:
```bash
python client_gui.py
```

3. Alur bermain:
- Masukkan username.
- Pilih **Quick Match** untuk matchmaking otomatis, atau **Create Room** dan minta pemain lain memilih **Join Room** memakai kode room.
- Gunakan tombol panah atas/bawah untuk menggerakkan paddle.
- Pemain pertama yang mencapai 10 poin menjadi pemenang.

## Konfigurasi Jaringan
Konfigurasi utama ada di `network_config.py`:
- `SERVER_IP`: alamat server.
- `SERVER_PORT`: port UDP server.
- `BUFFER_SIZE`: ukuran maksimal packet.
- `CLIENT_TIMEOUT`: batas waktu client dianggap disconnect.
- `FPS`: tick rate game dan render client.

Untuk bermain di jaringan lokal, ubah `SERVER_IP` di client menjadi IP komputer yang menjalankan server.

## Daftar Packet
| Packet | Arah | Fungsi |
| --- | --- | --- |
| `VERIFY_USERNAME` | Client -> Server | Validasi dan registrasi username |
| `USERNAME_ACCEPTED` | Server -> Client | Username diterima |
| `USERNAME_REJECTED` | Server -> Client | Username sedang dipakai |
| `CREATE_ROOM` | Client -> Server | Membuat room baru |
| `MATCHMAKE` | Client -> Server | Mencari room waiting atau membuat room baru |
| `JOIN_ROOM` | Client -> Server | Masuk ke room berdasarkan kode |
| `ROOM_CREATED` | Server -> Client | Room berhasil dibuat |
| `ROOM_JOINED` | Server -> Client | Client berhasil masuk room sebagai P1, P2, atau SPECTATOR |
| `STATE` | Server -> Client | Sinkronisasi state game |
| `MOVE` | Client -> Server | Mengirim posisi paddle pemain |
| `PING` | Client -> Server | Mengukur latency |
| `PONG` | Server -> Client | Balasan latency |
| `GET_LEADERBOARD` | Client -> Server | Meminta data ranking |
| `LEADERBOARD_DATA` | Server -> Client | Mengirim data ranking |
| `SURRENDER` | Client -> Server | Menyerah dari match |
| `EXIT_ROOM` | Client -> Server | Keluar dari room |
| `ROOM_CLOSED` | Server -> Client | Room ditutup oleh player aktif |

## Anti-invalid Packet
Server menolak packet yang:
- Tidak dapat di-decode sebagai JSON.
- Tidak memiliki `type` yang dikenal.
- Mengirim username kosong, terlalu panjang, atau mengandung karakter non-alfanumerik.
- Mengirim room code yang bukan 5 digit.
- Mengirim posisi paddle di luar area layar.

Validasi ini sederhana, tetapi cukup untuk menunjukkan bahwa server tidak langsung mempercayai packet dari client.

## Struktur File
```text
WiverBerth/
  client_gui.py       # GUI Pygame dan input client
  server_engine.py    # Dedicated UDP server, room, matchmaking, sync, replay
  network_config.py   # Konfigurasi jaringan, ukuran layar, codec JSON
  leaderboard.json    # Dibuat otomatis saat ada data ranking
  replays/            # Dibuat otomatis saat match selesai
```

## Screenshot Hasil

### Main Menu
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/5ba38c6a-cfcb-4a1c-adeb-6180ff2bab63" />

### Rules
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/3600486d-c99a-419e-a520-aea9fe63e811" />

### Leaderboard
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/855f2475-804f-4562-82dd-2c892e0fb256" />

### Input Username
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/3ebc5c8d-7f5c-4d53-afc0-c84862c582cf" />

### Halaman Setelah Login
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/f86f973f-df30-4565-b4c8-6de2293564ae" />

### Create Room (Masuk ke Match Room menunggu lawan)
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/00dbb630-0123-4923-be97-e8d31abbbdd9" />

### Quick Match (Sama seperti Create Room)
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/754e0db8-6515-4ac1-afd4-095d2d331f99" />

### Join Room (Input kode untuk join)
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/62306119-5045-4370-a648-51e6c87859f9" />

### Match Room (P1)
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/73f9437a-8c9e-4e24-8ae9-7852e4a2ec0e" />

### Match Room (P2)
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/d31fe96a-f886-4874-a0fc-d9390c772302" />

### Match Room (Spectator)
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/8d32b9e3-7768-4db2-bac6-3a9dcd5f44bb" />

### Saat match selesai
<img width="1002" height="790" alt="image" src="https://github.com/user-attachments/assets/5258d377-1931-4f95-85de-073016224c98" />


