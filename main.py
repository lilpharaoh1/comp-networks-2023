import socket
import time 
import numpy as np
import threading

def client_connect(client, dest, port):
    client.connect(dest, port)
    print(f"[{client.name}] Connection request sent to [{dest}, {port}]")

def client_thread(conn, addr):
    with conn:
        # image_handle, image_idx = np.zeros((32, 32), np.int8), 0
        print(f"[CONNECTION] Connection received at {addr}")
        while True:
            data = conn.recv(1024)
            print(f"[{addr}] Received Packet...")
    print(f"[CONNECTION] Disconnected from {addr}")


    # thread = threading.Thread(target=client_thread, args=(conn, addr))
    # return thread


class DroneAgent:
    def __init__(self, server_addr, server_dests):
        self.server_socket = None
        self.server_conns = []
        self.client_conns = []
        self.server_dests = server_dests # Read from a launch file in future
        self.connections = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server.bind(server_addr)
        self.server.listen(5)
        print(f"[INFO] Listening on {server_addr[0]}:{server_addr[1]}")
            
        thread = threading.Thread(target=self.open_server)
        thread.start()

        for ip, port in self.server_dests:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ip, port))
            print(f"[CONNECTION] Connection made at {ip}:{port}")
            self.client_conns.append(client)

        print(f"[INFO] DroneAgent {server_addr[0]}:{server_addr[1]} finished initiating")

    def open_server(self,):
        while True:
            conn, addr = self.server.accept()
            print(f"[INFO] Starting thread for connection {addr}")
            thread = threading.Thread(target=client_thread, args=(conn, addr))
            thread.start()

    def spin(self):
        while True:
            image = np.random.normal(size=(32,32)).tobytes()
            for client in self.client_conns:
                print(f"[INFO] {client} sending image...")
                client.send(image)
                time.sleep(20)

SERVER = socket.gethostbyname(socket.gethostname())

SERVER_ADDR = (socket.gethostbyname(socket.gethostname()), 9797)
server_dests = [
                ["192.168.56.1", 9797]
               ]
drone = DroneAgent(SERVER_ADDR, server_dests)
drone.spin()