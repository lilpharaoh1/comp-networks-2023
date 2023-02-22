import socket
import time 
import numpy as np
import threading

def client_thread(conn, addr):
    with conn:
        image_handle, image_idx = np.zeros((32, 32), np.int8), 0
        print(f"[CONNECTION] Connected to {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            image = np.frombuffer(data)
            print(f"[{addr}] Received Packet...")
    print(f"[CONNECTION] Disconnected from {addr}")

class DroneAgent:
    def __init__(self, client_server, server, port):
        self.server_threads = []
        self.server_dests = [client_server] # Read from a launch file in future
        self.server_ports = [port]          # Read from a launch file in future
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            
            s.bind((server, port))
            s.listen(5)
            print(f"[INFO] Listening on {server}:{port}")

            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            for idx, dest in enumerate(self.server_dests):
                client 
            self.client.connect((client_server, port))

            while True:
                conn, addr = s.accept()
                print(f"[INFO] Starting thread for connection {addr}")
                self.server_thread.append(threading.Thread(target=client_thread, args=(conn, addr)))

    def spin(self):
        for thread in self.server_threads:
            thread.start()

    def client_publish(self):
        image = np.random.normal(size=(32,32)).tobytes()
        self.client.send(image)

SERVER = socket.gethostbyname(socket.gethostname())
CLIENT_SERVER = "192.168.56.1"
PORT = 9797

drone = DroneAgent(CLIENT_SERVER, SERVER, PORT)
drone.spin()