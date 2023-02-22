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
        print(f"[CONNECTION] Connected to {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            image = np.frombuffer(data)
            print(f"[{addr}] Received Packet...")
    print(f"[CONNECTION] Disconnected from {addr}")


    # thread = threading.Thread(target=client_thread, args=(conn, addr))
    # return thread



class DroneAgent:
    def __init__(self, client_server, server, port):
        self.server_socket = None
        self.server = server
        self.port = port
        self.server_conns = []
        self.client_conns = []
        self.server_dests = [(client_server, port)] # Read from a launch file in future
        self.connections = []


        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                
            s.bind((self.server, self.port))
            s.listen(5)
            print(f"[INFO] Listening on {self.server}:{self.port}")
            
            for dest_x, port_x in self.server_dests:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_thread = threading.Thread(target=self.wait_for_connection)
                server_thread.start()
                # print("outside of thread...")
                client.connect((dest_x, port_x))
                # print(f"[INFO] {client} connection request sent to {dest_x}:{port_x}")
                # conn, addr = self.connections[-1]
                # self.server_conns.append(threading.Thread(target=client_thread, args=(conn, addr)))
                # self.clients.append(client)

    def wait_for_connection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                
            s.bind((self.server, self.port))
            s.listen(5)
            print(f"[INFO] Listening on {self.server}:{self.port}")
            print(f"[INFO] {s} waiting for connection")
            conn, addr = s.accept()
            print(f"[INFO] Starting thread for connection {addr}")
            self.connections.append((conn, addr))

    def spin(self):
        for thread in self.server_conns:
            thread.start()

        while True:
            image = np.random.normal(size=(32,32)).tobytes()
            for client in self.client:
                print(f"[INFO] {client.name} sending image...")
                client.send(image)
                time.wait(10)

    # def client_publish(self):
    #     image = np.random.normal(size=(32,32)).tobytes()
    #     self.client.send(image)

SERVER = socket.gethostbyname(socket.gethostname())
CLIENT_SERVER = "192.168.56.1"
PORT = 9797

drone = DroneAgent(CLIENT_SERVER, SERVER, PORT)
# drone.spin()