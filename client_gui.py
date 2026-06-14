import pygame
import socket
import threading
import time
from network_config import *

class PongClient:
    # fungsi untuk inisialisasi klien, termasuk setup GUI, koneksi socket
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("WiverBerth - Final Project")
        self.clock = pygame.time.Clock()
        
        self.font_small = pygame.font.SysFont("Courier", 20, bold=True)
        self.font = pygame.font.SysFont("Courier", 28, bold=True)
        self.title_font = pygame.font.SysFont("Courier", 45, bold=True)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(0.1) 
        
        self.app_state = 'HOME' 
        self.input_text = ""
        self.username = ""
        self.error_msg = ""
        
        self.room_code = None
        self.player_id = None
        self.paddle_y = HEIGHT // 2
        self.latency = 0
        self.server_state = {}
        self.leaderboard_data = []

    # fungsi untuk mendengarkan paket dari server secara terus-menerus
    def listen_server(self):
        while True:
            try:
                data, _ = self.client_socket.recvfrom(BUFFER_SIZE)
                packet = decode_packet(data)
                if not packet: continue

                p_type = packet['type']
                
                if p_type == 'USERNAME_ACCEPTED':
                    self.username = packet['username']
                    self.error_msg = ""
                    self.input_text = ""
                    self.app_state = 'ROOM_MENU'
                elif p_type == 'USERNAME_REJECTED':
                    self.error_msg = packet['msg']
                elif p_type == 'ROOM_CREATED' or p_type == 'ROOM_JOINED':
                    self.room_code = packet['code']
                    self.player_id = packet['id']
                    self.app_state = 'PLAYING'
                elif p_type == 'STATE':
                    self.server_state = packet['data']
                elif p_type == 'LEADERBOARD_DATA':
                    self.leaderboard_data = packet['data']
                    self.app_state = 'LEADERBOARD'
                elif p_type == 'ERROR':
                    self.error_msg = packet['msg']
                    self.app_state = 'ERROR'
                elif p_type == 'ROOM_CLOSED':
                    self.reset_client_data()
                    self.error_msg = "Room telah ditutup oleh Host."
                    self.app_state = 'ERROR'
                elif p_type == 'PONG':
                    self.latency = round((time.time() - packet['time']) * 1000)
            except:
                pass
    
    # fungsi untuk mereset data klien saat keluar dari room atau terjadi error
    def reset_client_data(self):
        self.room_code = None
        self.player_id = None
        self.server_state = {}
        self.input_text = ""

    # fungsi untuk menggambar tombol dengan efek hover dan menangani klik
    def draw_button(self, text, x, y, w, h, active_color, inactive_color, mouse_pos):
        rect = pygame.Rect(x, y, w, h)
        is_hover = rect.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, active_color if is_hover else inactive_color, rect, border_radius=10)
        text_surf = self.font.render(text, True, TEXT_COLOR)
        self.screen.blit(text_surf, (x + (w - text_surf.get_width())//2, y + (h - text_surf.get_height())//2))
        return rect

    # fungsi utama untuk menggambar semua elemen GUI berdasarkan state aplikasi saat ini
    def draw_gui(self):
        self.screen.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()
        clicked = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            
            if self.app_state == 'USERNAME_INPUT' and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and len(self.input_text) > 0:
                    self.client_socket.sendto(encode_packet({'type': 'VERIFY_USERNAME', 'username': self.input_text}), (SERVER_IP, SERVER_PORT))
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                    self.error_msg = ""
                elif len(self.input_text) < 10 and event.unicode.isalnum():
                    self.input_text += event.unicode
                    self.error_msg = ""

            elif self.app_state == 'JOIN_INPUT' and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and len(self.input_text) == 5:
                    self.client_socket.sendto(encode_packet({
                        'type': 'JOIN_ROOM', 'username': self.username, 'code': self.input_text
                    }), (SERVER_IP, SERVER_PORT))
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif event.unicode.isnumeric() and len(self.input_text) < 5:
                    self.input_text += event.unicode

        if self.app_state == 'HOME':
            title = self.title_font.render("WiverBerth Pong Game", True, P1_COLOR)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
            
            btn_start = self.draw_button("START GAME", WIDTH//2 - 150, 180, 300, 50, (40, 180, 40), (30, 140, 30), mouse_pos)
            btn_rules = self.draw_button("RULES", WIDTH//2 - 150, 250, 300, 50, (60, 60, 180), (40, 40, 140), mouse_pos)
            btn_leader = self.draw_button("LEADERBOARD", WIDTH//2 - 150, 320, 300, 50, (180, 180, 40), (140, 140, 30), mouse_pos)
            btn_exit = self.draw_button("EXIT", WIDTH//2 - 150, 390, 300, 50, (180, 60, 60), (140, 40, 40), mouse_pos)
            
            if clicked:
                if btn_start.collidepoint(mouse_pos): 
                    self.input_text = ""
                    self.error_msg = ""
                    self.app_state = 'USERNAME_INPUT'
                if btn_rules.collidepoint(mouse_pos):
                    self.app_state = 'RULES'
                if btn_leader.collidepoint(mouse_pos):
                    self.client_socket.sendto(encode_packet({'type': 'GET_LEADERBOARD'}), (SERVER_IP, SERVER_PORT))
                if btn_exit.collidepoint(mouse_pos): pygame.quit(); exit()

        elif self.app_state == 'USERNAME_INPUT':
            title = self.font.render("MASUKKAN USERNAME ANDA:", True, TEXT_COLOR)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 200))
            
            pygame.draw.rect(self.screen, (30, 30, 40), (WIDTH//2 - 150, 260, 300, 60), border_radius=8)
            pygame.draw.rect(self.screen, P2_COLOR, (WIDTH//2 - 150, 260, 300, 60), width=3, border_radius=8)
            
            input_surf = self.title_font.render(self.input_text, True, TEXT_COLOR)
            self.screen.blit(input_surf, (WIDTH//2 - input_surf.get_width()//2, 270))
            
            hint = self.font_small.render("Maksimal 10 huruf, tekan ENTER", True, (150, 150, 150))
            self.screen.blit(hint, (WIDTH//2 - hint.get_width()//2, 350))

            if self.error_msg:
                err_surf = self.font_small.render(self.error_msg, True, (255, 80, 80))
                self.screen.blit(err_surf, (WIDTH//2 - err_surf.get_width()//2, 380))

            btn_back = self.draw_button("KEMBALI", 20, 20, 120, 40, (180, 60, 60), (140, 40, 40), mouse_pos)
            if clicked and btn_back.collidepoint(mouse_pos):
                self.input_text = ""
                self.error_msg = ""
                self.app_state = 'HOME'

        elif self.app_state == 'RULES':
            title = self.title_font.render("CARA BERMAIN", True, P2_COLOR)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
            
            rules = [
                "1. Game membutuhkan 2 pemain dalam 1 Room.",
                "2. Gunakan Panah Atas dan Bawah untuk bergerak.",
                "3. Pemain pertama yang mencapai 10 Poin menang.",
                "4. Quick Match akan mencari lawan otomatis.",
                "5. Pemain ke-3 dan seterusnya akan menjadi Penonton."
            ]
            for i, rule in enumerate(rules):
                r_text = self.font_small.render(rule, True, TEXT_COLOR)
                self.screen.blit(r_text, (80, 180 + (i*40)))
                
            btn_back = self.draw_button("KEMBALI", WIDTH//2 - 100, 450, 200, 50, (100, 100, 100), (70, 70, 70), mouse_pos)
            if clicked and btn_back.collidepoint(mouse_pos): self.app_state = 'HOME'

        elif self.app_state == 'LEADERBOARD':
            title = self.title_font.render("GLOBAL RANKING", True, BALL_COLOR)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
            
            for i, data in enumerate(self.leaderboard_data):
                lb_text = self.font.render(f"{i+1}. {data['name']} - {data['wins']} Wins", True, TEXT_COLOR)
                self.screen.blit(lb_text, (WIDTH//2 - 150, 130 + (i*40)))
                
            btn_back = self.draw_button("KEMBALI", WIDTH//2 - 100, 500, 200, 50, (100, 100, 100), (70, 70, 70), mouse_pos)
            if clicked and btn_back.collidepoint(mouse_pos): self.app_state = 'HOME'

        elif self.app_state == 'ROOM_MENU':
            welcome = self.font.render(f"Welcome, {self.username}!", True, P1_COLOR)
            self.screen.blit(welcome, (WIDTH//2 - welcome.get_width()//2, 100))
            
            btn_create = self.draw_button("CREATE ROOM", WIDTH//2 - 150, 185, 300, 50, (0, 200, 200), (0, 150, 150), mouse_pos)
            btn_quick = self.draw_button("QUICK MATCH", WIDTH//2 - 150, 255, 300, 50, (40, 180, 40), (30, 140, 30), mouse_pos)
            btn_join = self.draw_button("JOIN ROOM", WIDTH//2 - 150, 325, 300, 50, (200, 100, 0), (150, 70, 0), mouse_pos)
            btn_logout = self.draw_button("LOGOUT", 20, 20, 120, 40, (180, 60, 60), (140, 40, 40), mouse_pos)
            
            if clicked:
                if btn_create.collidepoint(mouse_pos):
                    self.client_socket.sendto(encode_packet({'type': 'CREATE_ROOM', 'username': self.username}), (SERVER_IP, SERVER_PORT))
                if btn_quick.collidepoint(mouse_pos):
                    self.client_socket.sendto(encode_packet({'type': 'MATCHMAKE', 'username': self.username}), (SERVER_IP, SERVER_PORT))
                if btn_join.collidepoint(mouse_pos):
                    self.input_text = ""
                    self.app_state = 'JOIN_INPUT'
                if btn_logout.collidepoint(mouse_pos):
                    self.client_socket.sendto(encode_packet({'type': 'LOGOUT'}), (SERVER_IP, SERVER_PORT))
                    self.username = ""
                    self.reset_client_data()
                    self.app_state = 'HOME'

        elif self.app_state == 'JOIN_INPUT':
            title = self.font.render("MASUKKAN 5 ANGKA ROOM CODE:", True, TEXT_COLOR)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 200))
            
            pygame.draw.rect(self.screen, (30, 30, 40), (WIDTH//2 - 100, 260, 200, 60), border_radius=8)
            pygame.draw.rect(self.screen, BALL_COLOR, (WIDTH//2 - 100, 260, 200, 60), width=3, border_radius=8)
            
            input_surf = self.title_font.render(self.input_text, True, TEXT_COLOR)
            self.screen.blit(input_surf, (WIDTH//2 - input_surf.get_width()//2, 270))

            btn_back = self.draw_button("BATAL", 20, 20, 120, 40, (180, 60, 60), (140, 40, 40), mouse_pos)
            if clicked and btn_back.collidepoint(mouse_pos): self.app_state = 'ROOM_MENU'

        elif self.app_state == 'ERROR':
            err_text = self.font.render(self.error_msg, True, (255, 100, 100))
            self.screen.blit(err_text, (WIDTH//2 - err_text.get_width()//2, HEIGHT//2 - 50))
            btn_ok = self.draw_button("OKE", WIDTH//2 - 75, HEIGHT//2 + 30, 150, 50, (100, 100, 100), (70, 70, 70), mouse_pos)
            if clicked and btn_ok.collidepoint(mouse_pos): 
                self.app_state = 'ROOM_MENU' if self.username else 'HOME'

        elif self.app_state == 'PLAYING':
            for i in range(0, HEIGHT, 40):
                pygame.draw.rect(self.screen, (50, 50, 60), (WIDTH//2 - 2, i, 4, 20))

            status = self.server_state.get('status')
            p1_name = self.server_state.get('p1_name', '')
            p2_name = self.server_state.get('p2_name', '')
            
            code_text = self.font_small.render(f"ROOM CODE: {self.room_code} | {p1_name} VS {p2_name}", True, BALL_COLOR)
            self.screen.blit(code_text, (WIDTH//2 - code_text.get_width()//2, 60))

            if not self.server_state:
                text = self.title_font.render("MENYAMBUNGKAN...", True, TEXT_COLOR)
                self.screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2))

            elif status == 'WAITING':
                text = self.title_font.render("WAITING FOR OPPONENT...", True, TEXT_COLOR)
                self.screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2))
                
                btn_cancel = self.draw_button("BATAL & KELUAR ROOM", WIDTH//2 - 175, HEIGHT//2 + 60, 350, 50, (180, 60, 60), (140, 40, 40), mouse_pos)
                if clicked and btn_cancel.collidepoint(mouse_pos):
                    self.client_socket.sendto(encode_packet({'type': 'EXIT_ROOM'}), (SERVER_IP, SERVER_PORT))
                    self.reset_client_data()
                    self.app_state = 'ROOM_MENU'
                    
            elif status == 'PAUSED':
                text_main = self.title_font.render("GAME PAUSED", True, (255, 100, 100))
                text_sub = self.font.render("WAITING OTHER PLAYER TO RECONNECT...", True, (200, 200, 200))
                self.screen.blit(text_main, (WIDTH//2 - text_main.get_width()//2, HEIGHT//2 - 30))
                self.screen.blit(text_sub, (WIDTH//2 - text_sub.get_width()//2, HEIGHT//2 + 20))
            
            elif status == 'ENDED':
                winner = self.server_state.get('winner', '')
                win_text = self.title_font.render(f"{winner} WINS THE MATCH!", True, P1_COLOR)
                self.screen.blit(win_text, (WIDTH//2 - win_text.get_width()//2, HEIGHT//2 - 30))
                
                btn_exit = self.draw_button("KELUAR ROOM", WIDTH//2 - 150, HEIGHT//2 + 50, 300, 50, (180, 60, 60), (140, 40, 40), mouse_pos)
                if clicked and btn_exit.collidepoint(mouse_pos):
                    self.client_socket.sendto(encode_packet({'type': 'EXIT_ROOM'}), (SERVER_IP, SERVER_PORT))
                    self.reset_client_data()
                    self.app_state = 'ROOM_MENU'
            else:
                pygame.draw.circle(self.screen, BALL_COLOR, (int(self.server_state['ball_x']), int(self.server_state['ball_y'])), 10)
                pygame.draw.rect(self.screen, P1_COLOR, (30, self.server_state['p1_y'] - 40, 15, 80))
                pygame.draw.rect(self.screen, P2_COLOR, (WIDTH - 45, self.server_state['p2_y'] - 40, 15, 80))
                
                score_text = self.title_font.render(f"{self.server_state['score1']} - {self.server_state['score2']}", True, TEXT_COLOR)
                self.screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 10))
                
                # Tombol Surrender hanya untuk P1 & P2, dan tombol Leave untuk Spectator
                if self.player_id in ['P1', 'P2']:
                    btn_surrender = self.draw_button("SURRENDER", WIDTH//2 - 90, HEIGHT - 55, 180, 40, (230, 40, 40), (170, 30, 30), mouse_pos)
                    if clicked and btn_surrender.collidepoint(mouse_pos):
                        self.client_socket.sendto(encode_packet({'type': 'SURRENDER'}), (SERVER_IP, SERVER_PORT))
                else:
                    btn_leave = self.draw_button("LEAVE ROOM", WIDTH//2 - 90, HEIGHT - 55, 180, 40, (150, 150, 150), (100, 100, 100), mouse_pos)
                    if clicked and btn_leave.collidepoint(mouse_pos):
                        self.client_socket.sendto(encode_packet({'type': 'EXIT_ROOM'}), (SERVER_IP, SERVER_PORT))
                        self.reset_client_data()
                        self.app_state = 'ROOM_MENU'

            role_color = (150, 150, 150) if self.player_id == 'SPECTATOR' else (0, 255, 255)
            id_text = self.font_small.render(f"ROLE: {self.player_id}", True, role_color)
            self.screen.blit(id_text, (WIDTH - id_text.get_width() - 20, 10))
            ping_text = self.font_small.render(f"Ping: {self.latency}ms", True, (0, 255, 0))
            self.screen.blit(ping_text, (10, 10))

        pygame.display.flip()

    # fungsi utama untuk menjalankan loop game
    def run(self):
        threading.Thread(target=self.listen_server, daemon=True).start()
        last_ping_time = time.time()

        while True:
            current_time = time.time()
            if current_time - last_ping_time > 1.0:
                self.client_socket.sendto(encode_packet({'type': 'PING', 'time': current_time}), (SERVER_IP, SERVER_PORT))
                last_ping_time = current_time

            if self.app_state == 'PLAYING' and self.player_id in ['P1', 'P2']:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP] and self.paddle_y > 40:
                    self.paddle_y -= 8
                if keys[pygame.K_DOWN] and self.paddle_y < HEIGHT - 40:
                    self.paddle_y += 8
                if self.server_state.get('status') == 'PLAYING':
                    self.client_socket.sendto(encode_packet({'type': 'MOVE', 'y': self.paddle_y}), (SERVER_IP, SERVER_PORT))

            self.draw_gui()
            self.clock.tick(FPS)

if __name__ == "__main__":
    client = PongClient()
    client.run()
