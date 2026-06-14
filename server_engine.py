import socket
import threading
import time
import logging
import random
import os
import json
from network_config import *

# logging di terminal server untuk melihat aktivitas dan debugging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD_FILE = os.path.join(BASE_DIR, "leaderboard.json")
REPLAY_DIR = os.path.join(BASE_DIR, "replays")
VALID_PACKET_TYPES = {
    'VERIFY_USERNAME', 'CREATE_ROOM', 'MATCHMAKE', 'JOIN_ROOM', 'GET_LEADERBOARD',
    'MOVE', 'PING', 'LOGOUT', 'SURRENDER', 'EXIT_ROOM'
}

class PongServer:
    # fungsi untuk inisialisasi server, membuat socket UDP, dan struktur data untuk menyimpan state game, room, dan leaderboard
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((SERVER_IP, SERVER_PORT))
        
        self.rooms = {} 
        self.client_room_map = {} 
        self.leaderboard_db = self.load_leaderboard()
        self.active_usernames = {}
        self.client_last_seen = {} 
        os.makedirs(REPLAY_DIR, exist_ok=True)

    # fungsi untuk membuat state awal game baru yg digunakan saat membuat room baru atau reset ball setelah skor
    def create_new_state(self):
        return {
            'ball_x': WIDTH // 2, 'ball_y': HEIGHT // 2, # posisi awal bola di tengah
            'p1_y': HEIGHT // 2, 'p2_y': HEIGHT // 2, # posisi awal pemain di tengah
            'score1': 0, 'score2': 0,
            'status': 'WAITING', 'winner': '',
            'p1_name': 'Waiting...', 'p2_name': 'Waiting...'
        }

    # fungsi untuk mereset posisi bola ke tengah setelah terjadi skor
    def reset_ball(self, room_state):
        room_state['ball_x'] = WIDTH // 2
        room_state['ball_y'] = HEIGHT // 2
        time.sleep(1)

    # fungsi untuk memuat data leaderboard dari file JSON
    def load_leaderboard(self):
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                return data
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.warning(f"Gagal membaca leaderboard: {e}")
        return {}
    
    # fungsi untuk menyimpan data leaderboard ke file JSON
    def save_leaderboard(self):
        try:
            with open(LEADERBOARD_FILE, "w", encoding="utf-8") as file:
                json.dump(self.leaderboard_db, file, indent=2)
        except Exception as e:
            logging.warning(f"Gagal menyimpan leaderboard: {e}")

    #fungsi untuk memastikan bahwa setiap username yang digunakan memiliki catatan di database leaderboard, jika belum ada maka dibuatkan dengan 0 wins
    def ensure_user_record(self, username):
        if username and username not in self.leaderboard_db:
            self.leaderboard_db[username] = {'wins': 0}
            self.save_leaderboard()

    # fungsi untuk memvalidasi paket yang diterima dari klien
    def validate_packet(self, packet):
        if not isinstance(packet, dict):
            return False
        packet_type = packet.get('type')
        if packet_type not in VALID_PACKET_TYPES:
            return False

        if packet_type in ['VERIFY_USERNAME', 'CREATE_ROOM', 'MATCHMAKE', 'JOIN_ROOM']:
            username = packet.get('username')
            if not isinstance(username, str) or not username.strip() or len(username.strip()) > 10:
                return False
            if not username.strip().isalnum():
                return False

        if packet_type == 'JOIN_ROOM':
            code = packet.get('code')
            if not isinstance(code, str) or not code.isdigit() or len(code) != 5:
                return False

        if packet_type == 'MOVE':
            y = packet.get('y')
            if not isinstance(y, (int, float)) or not 0 <= y <= HEIGHT:
                return False

        return True

    # fungsi untuk membuat room baru untuk pemain yang membuat room, menghasilkan kode unik, dan menyimpan state awal dan informasi klien
    def create_room_for(self, addr, username):
        room_code = str(random.randint(10000, 99999))
        while room_code in self.rooms:
            room_code = str(random.randint(10000, 99999))

        self.rooms[room_code] = {
            'state': self.create_new_state(),
            'clients': {addr: {'id': 'P1', 'username': username, 'last_seen': time.time()}},
            'ball_dx': 5, 'ball_dy': 5,
            'replay': [],
            'replay_tick': 0,
            'replay_saved': False
        }
        self.rooms[room_code]['state']['p1_name'] = username
        self.client_room_map[addr] = room_code
        self.active_usernames[addr] = username
        self.ensure_user_record(username)
        return room_code

    # fungsi untuk menambahkan pemain kedua ke room yang sudah dibuat, memperbarui state, dan mengirim konfirmasi ke klien
    def join_as_player_two(self, room_code, addr, username):
        room = self.rooms[room_code]
        state = room['state']
        room['clients'][addr] = {'id': 'P2', 'username': username, 'last_seen': time.time()}
        state['p2_name'] = username
        state['status'] = 'PLAYING'
        self.active_usernames[addr] = username
        self.client_room_map[addr] = room_code
        self.ensure_user_record(username)
        logging.info(f"{username} join Room {room_code} sebagai P2")
        self.server_socket.sendto(encode_packet({'type': 'ROOM_JOINED', 'code': room_code, 'id': 'P2'}), addr)

    #fungsi untuk menyimpan replay pertandingan ke file JSON setelah match selesai
    def save_replay(self, room_code, room, reason):
        if room.get('replay_saved'):
            return
        state = room['state']
        replay_data = {
            'room_code': room_code,
            'reason': reason,
            'winner': state.get('winner', ''),
            'p1_name': state.get('p1_name', ''),
            'p2_name': state.get('p2_name', ''),
            'final_score': [state.get('score1', 0), state.get('score2', 0)],
            'frames': room.get('replay', [])
        }
        filename = f"replay_{room_code}_{int(time.time())}.json"
        path = os.path.join(REPLAY_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(replay_data, file, indent=2)
            room['replay_saved'] = True
            logging.info(f"Replay match disimpan: {path}")
        except Exception as e:
            logging.warning(f"Gagal menyimpan replay: {e}")

    #fungsi untuk mengakhiri match
    def finish_match(self, room_code, room, winner_name, reason):
        state = room['state']
        if state['status'] == 'ENDED':
            return
        state['status'] = 'ENDED'
        state['winner'] = winner_name
        self.ensure_user_record(winner_name)
        self.leaderboard_db[winner_name]['wins'] += 1
        self.save_leaderboard()
        self.save_replay(room_code, room, reason)

    # fungsi untuk mencatat frame replay setiap 6 tick saat status game PLAYING, menyimpan posisi bola, pemain, dan skor untuk setiap frame yang dicatat
    def record_replay_frame(self, room):
        room['replay_tick'] += 1
        if room['replay_tick'] % 6 != 0:
            return
        state = room['state']
        room['replay'].append({
            't': room['replay_tick'],
            'ball_x': state['ball_x'],
            'ball_y': state['ball_y'],
            'p1_y': state['p1_y'],
            'p2_y': state['p2_y'],
            'score1': state['score1'],
            'score2': state['score2']
        })

    # fungsi untuk memeriksa timeout klien yang tidak aktif dan untuk reconnect handling
    def check_timeouts(self):
        while True:
            time.sleep(1)
            current_time = time.time()
            for code, room in list(self.rooms.items()):
                state = room['state']
                if state['status'] == 'PLAYING':
                    for addr, info in list(room['clients'].items()):
                        # Jika paket terhenti > 3 detik
                        if info['id'] in ['P1', 'P2'] and current_time - info['last_seen'] > CLIENT_TIMEOUT:
                            state['status'] = 'PAUSED'
                            logging.warning(f"{info['username']} terputus dari Room {code}. Menunggu reconnect...")

    # fungsi utama untuk mendengarkan paket dari klien, memvalidasi, dan merespons sesuai dengan jenis paket yang diterima
    def listen_clients(self):
        logging.info(f"Server Multi-Room Berjalan di Port {SERVER_PORT}")
        while True:
            try:
                data, addr = self.server_socket.recvfrom(BUFFER_SIZE)
                packet = decode_packet(data)
                if not packet:
                    continue
                if not self.validate_packet(packet):
                    logging.warning(f"Invalid packet dari {addr}: {packet}")
                    continue
                
                packet_type = packet.get('type')

                # catat setiap ada sinyal masuk dari klien
                self.client_last_seen[addr] = time.time()
                
                # pembaruan koneksi terakhir klien
                if addr in self.client_room_map:
                    code = self.client_room_map[addr]
                    if code in self.rooms and addr in self.rooms[code]['clients']:
                        self.rooms[code]['clients'][addr]['last_seen'] = time.time()

                if packet_type == 'VERIFY_USERNAME':
                    username = packet.get('username', '').strip()
                    
                    old_addr = None
                    for a, u in list(self.active_usernames.items()):
                        if u == username:
                            old_addr = a
                            break

                    if old_addr and old_addr != addr:
                        last_ping = self.client_last_seen.get(old_addr, 0)
                        
                        # Jika ada PING dalam 3 detik terakhir (klien masih buka aplikasi di menu manapun)
                        if time.time() - last_ping < CLIENT_TIMEOUT:
                            self.server_socket.sendto(encode_packet({'type': 'USERNAME_REJECTED', 'msg': 'Username sedang dipakai!'}), addr)
                            continue
                        else:
                            # Jika sudah Force Close > 3 detik, ambil alih username
                            self.active_usernames.pop(old_addr, None)
                            self.client_room_map.pop(old_addr, None)
                            
                    # Daftarkan alamat port baru ke username ini
                    self.active_usernames[addr] = username
                    self.ensure_user_record(username)
                    self.server_socket.sendto(encode_packet({'type': 'USERNAME_ACCEPTED', 'username': username}), addr)

                elif packet_type == 'CREATE_ROOM':
                    username = packet.get('username', '').strip()
                    if username in self.active_usernames.values() and self.active_usernames.get(addr) != username:
                        self.server_socket.sendto(encode_packet({'type': 'ERROR', 'msg': 'Sesi bentrok, silakan login ulang.'}), addr)
                        continue

                    room_code = self.create_room_for(addr, username)
                    logging.info(f"Room {room_code} dibuat oleh {username}")
                    self.server_socket.sendto(encode_packet({'type': 'ROOM_CREATED', 'code': room_code, 'id': 'P1'}), addr)

                elif packet_type == 'MATCHMAKE':
                    username = packet.get('username', '').strip()
                    if username in self.active_usernames.values() and self.active_usernames.get(addr) != username:
                        self.server_socket.sendto(encode_packet({'type': 'ERROR', 'msg': 'Username sudah dipakai orang lain!'}), addr)
                        continue

                    matched_code = None
                    for code, room in self.rooms.items():
                        clients = list(room['clients'].values())
                        if room['state']['status'] == 'WAITING' and len(clients) == 1 and clients[0]['id'] == 'P1':
                            matched_code = code
                            break

                    if matched_code:
                        self.join_as_player_two(matched_code, addr, username)
                        logging.info(f"Quick Match: {username} otomatis masuk Room {matched_code}")
                    else:
                        room_code = self.create_room_for(addr, username)
                        logging.info(f"Quick Match: {username} menunggu lawan di Room {room_code}")
                        self.server_socket.sendto(encode_packet({'type': 'ROOM_CREATED', 'code': room_code, 'id': 'P1'}), addr)

                elif packet_type == 'JOIN_ROOM':
                    username = packet.get('username', '').strip()
                    code = packet.get('code')
                    
                    if username in self.active_usernames.values() and self.active_usernames.get(addr) != username:
                        self.server_socket.sendto(encode_packet({'type': 'ERROR', 'msg': 'Username sudah dipakai orang lain!'}), addr)
                        continue

                    if code in self.rooms:
                        room = self.rooms[code]
                        state = room['state']
                        
                        # logika untuk reconnect
                        if state['status'] == 'PAUSED' and (username == state['p1_name'] or username == state['p2_name']):
                            reconnect_id = 'P1' if username == state['p1_name'] else 'P2'
                            
                            old_addrs = [a for a, v in room['clients'].items() if v['username'] == username]
                            for a in old_addrs:
                                del room['clients'][a]
                                self.client_room_map.pop(a, None)
                                
                            room['clients'][addr] = {'id': reconnect_id, 'username': username, 'last_seen': time.time()}
                            self.active_usernames[addr] = username
                            self.client_room_map[addr] = code
                            state['status'] = 'PLAYING'
                            
                            logging.info(f"{username} RECONNECT ke Room {code}. Game dilanjutkan.")
                            self.server_socket.sendto(encode_packet({'type': 'ROOM_JOINED', 'code': code, 'id': reconnect_id}), addr)
                            continue 

                        # logika untuk join normal (sebagai P2 atau spectator)
                        self.ensure_user_record(username)
                        
                        self.active_usernames[addr] = username
                        self.client_room_map[addr] = code

                        if len(room['clients']) == 1 and list(room['clients'].values())[0]['id'] == 'P1':
                            self.join_as_player_two(code, addr, username)
                        else:
                            room['clients'][addr] = {'id': 'SPECTATOR', 'username': username, 'last_seen': time.time()}
                            logging.info(f"{username} join Room {code} sebagai SPECTATOR")
                            self.server_socket.sendto(encode_packet({'type': 'ROOM_JOINED', 'code': code, 'id': 'SPECTATOR'}), addr)
                    else:
                        self.server_socket.sendto(encode_packet({'type': 'ERROR', 'msg': 'Room Tidak Ditemukan!'}), addr)

                elif packet_type == 'GET_LEADERBOARD':
                    sorted_lb = sorted(self.leaderboard_db.items(), key=lambda x: x[1]['wins'], reverse=True)[:8]
                    formatted_lb = [{'name': k, 'wins': v['wins']} for k, v in sorted_lb]
                    self.server_socket.sendto(encode_packet({'type': 'LEADERBOARD_DATA', 'data': formatted_lb}), addr)

                elif packet_type == 'MOVE':
                    code = self.client_room_map.get(addr)
                    if code and code in self.rooms:
                        room = self.rooms[code]
                        if room['state']['status'] == 'PLAYING':
                            new_y = packet.get('y')
                            if isinstance(new_y, (int, float)) and 0 <= new_y <= HEIGHT:
                                player_id = room['clients'][addr]['id']
                                if player_id == 'P1': room['state']['p1_y'] = new_y
                                elif player_id == 'P2': room['state']['p2_y'] = new_y

                elif packet_type == 'PING':
                    self.server_socket.sendto(encode_packet({'type': 'PONG', 'time': packet.get('time', 0)}), addr)

                elif packet_type == 'LOGOUT':
                    username = self.active_usernames.pop(addr, None)
                    self.client_room_map.pop(addr, None)
                    logging.info(f"User {username} logout ke Main Menu.")

                elif packet_type == 'SURRENDER':
                    code = self.client_room_map.get(addr)
                    if code and code in self.rooms:
                        room = self.rooms[code]
                        state = room['state']
                        if addr in room['clients']:
                            player_id = room['clients'][addr]['id']
                            if player_id in ['P1', 'P2']:
                                winner_name = state['p2_name'] if player_id == 'P1' else state['p1_name']
                                self.finish_match(code, room, winner_name, "surrender")
                                logging.info(f"{room['clients'][addr]['username']} SURRENDER. {winner_name} Menang!")

                elif packet_type == 'EXIT_ROOM':
                    code = self.client_room_map.get(addr)
                    if code and code in self.rooms:
                        player_id = self.rooms[code]['clients'][addr]['id']
                        if player_id in ['P1', 'P2']:
                            for client_addr in list(self.rooms[code]['clients'].keys()):
                                if client_addr != addr:
                                    self.server_socket.sendto(encode_packet({'type': 'ROOM_CLOSED'}), client_addr)
                                self.client_room_map.pop(client_addr, None)
                            del self.rooms[code]
                            logging.info(f"Room {code} dihapus karena host/pemain keluar.")
                        else:
                            del self.rooms[code]['clients'][addr]
                            self.client_room_map.pop(addr, None)

            except Exception as e:
                pass
    
    # fungsi utama untuk menjalankan loop game, memperbarui posisi bola, memeriksa tabrakan, mencatat replay, dan mengirim state terbaru ke semua klien di setiap room
    def game_loop(self):
        while True:
            time.sleep(1/FPS)
            for code in list(self.rooms.keys()):
                if code not in self.rooms: continue
                room = self.rooms[code]
                state = room['state']

                state_packet = encode_packet({'type': 'STATE', 'data': state})
                for client_addr in list(room['clients'].keys()):
                    try:
                        self.server_socket.sendto(state_packet, client_addr)
                    except:
                        pass

                if state['status'] == 'PLAYING':
                    self.record_replay_frame(room)
                    state['ball_y'] += room['ball_dy']
                    if state['ball_y'] <= 0 or state['ball_y'] >= HEIGHT:
                        room['ball_dy'] *= -1
                    state['ball_x'] += room['ball_dx']
                    
                    if state['ball_x'] <= 45:
                        if state['p1_y'] - 40 <= state['ball_y'] <= state['p1_y'] + 40:
                            room['ball_dx'] *= -1
                            state['ball_x'] = 46
                        elif state['ball_x'] <= 0:
                            state['score2'] += 1
                            if state['score2'] >= 10:
                                self.finish_match(code, room, state['p2_name'], "score_limit")
                            else:
                                room['ball_dx'] *= -1
                                self.reset_ball(state)

                    elif state['ball_x'] >= WIDTH - 45: 
                        if state['p2_y'] - 40 <= state['ball_y'] <= state['p2_y'] + 40:
                            room['ball_dx'] *= -1
                            state['ball_x'] = WIDTH - 46
                        elif state['ball_x'] >= WIDTH:
                            state['score1'] += 1
                            if state['score1'] >= 10:
                                self.finish_match(code, room, state['p1_name'], "score_limit")
                            else:
                                room['ball_dx'] *= -1
                                self.reset_ball(state)

if __name__ == "__main__":
    server = PongServer()
    threading.Thread(target=server.listen_clients, daemon=True).start()
    threading.Thread(target=server.check_timeouts, daemon=True).start()
    server.game_loop()
