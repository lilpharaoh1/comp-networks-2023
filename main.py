import socket
import time 
import numpy as np
import threading
import argparse

def client_thread(conn, addr):
    with conn:
        # image_handle, image_idx = np.zeros((32, 32), np.int8), 0
        print(f"[CONNECTION] Connection received at {addr}")
        while True:
            data = conn.recv(1024)
            print(f"[{addr}] Received Packet...")
    print(f"[CONNECTION] Disconnected from {addr}")


class DroneAgent:
    def __init__(self, server_addr, server_dests):
        self.server_dests = server_dests # Read from a launch file in future
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_conns = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) for _ in server_dests]


        self.server.bind(server_addr)
        self.server.listen(5)
        print(f"[INFO] Listening on {server_addr[0]}:{server_addr[1]}")
            
        thread = threading.Thread(target=self.open_server)
        thread.start()

        thread = threading.Thread(target=self.search_for_conns)
        thread.start()

        print(f"[INFO] DroneAgent {server_addr[0]}:{server_addr[1]} finished initiating")

    def open_server(self):
        while True:
            conn, addr = self.server.accept()
            print(f"[INFO] Starting thread for connection {addr}")
            thread = threading.Thread(target=client_thread, args=(conn, addr))
            thread.start()
    
    def search_for_conns(self):
        while True: 
            for idx, client in enumerate(self.client_conns):
                try: 
                    client.send(1)
                    
                except:
                    try:
                        ip, port = self.server_dests[idx]
                        client.connect((ip, port))
                        print(f"[CONNECTION] Connection made at {ip}:{port}")
                        self.client_conns.append(client)
                    except:
                        # print(f"[CONNECTION] Unable to connect to {ip}:{port}")
                        pass
            time.sleep(60)
                

    def spin(self):
        while True:
            image = np.random.normal(size=(32,32)).tobytes()
            for client in self.client_conns:
                try:
                    print(f"[INFO] {client} sending image...")
                    client.send(image)
                except:
                    pass 
            time.sleep(10)

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--server-ip', default=socket.gethostbyname(socket.gethostname()), type=str)
parser.add_argument('-p', '--server-port', default=9797, type=int)
args = parser.parse_args()

SERVER_ADDR = (args.server_ip, args.server_port)
server_dests = [
                ["192.168.56.1", 9797],
                ["192.168.56.1", 9898]
               ]

print(SERVER_ADDR[0])
drone = DroneAgent(SERVER_ADDR, server_dests)
drone.spin()