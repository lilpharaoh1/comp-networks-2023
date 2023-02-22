import socket
import threading
import numpy as np
from matplotlib import pyplot as plt
import time


SERVER = socket.gethostbyname(socket.gethostname())
PORT = 9797


def client_thread(conn, addr):
    with conn:
        image_handle, image_idx = np.zeros((1024, 1024), np.int8), 0
        print(f"[CONNECTION] Connected to {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            image = np.frombuffer(data)
            print(len(image))
    print(f"[CONNECTION] Disconnected from {addr}")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((SERVER, PORT))
    s.listen(5)
    print(f"[INFO] Listening on {SERVER}:{PORT}")

    while True:
        conn, addr = s.accept()
        print(f"[INFO] Starting thread for connection {addr}")
        thread = threading.Thread(target=client_thread, args=(conn, addr))
        thread.start()