import json

# Konfigurasi Jaringan
SERVER_IP = '127.0.0.1'
SERVER_PORT = 7777 
BUFFER_SIZE = 2048
CLIENT_TIMEOUT = 3.0 # waktu toleransi untuk koneksi client (deteksi disconnect)

# Resolusi & Frame Rate GUI
WIDTH, HEIGHT = 800, 600
FPS = 60

# Tema Visual 
BG_COLOR = (15, 15, 20)
P1_COLOR = (0, 255, 255)   
P2_COLOR = (255, 0, 127)   
BALL_COLOR = (255, 255, 0) 
TEXT_COLOR = (240, 240, 240)

def encode_packet(data_dict):
    return json.dumps(data_dict).encode('utf-8')

def decode_packet(data_bytes):
    try:
        return json.loads(data_bytes.decode('utf-8'))
    except Exception:
        return None