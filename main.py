import socket
import time 
import numpy as np
import threading
import argparse
import os
import json
from PIL import Image
from pickle import dumps, loads
import yaml

IMAGE_SHAPE = (12, 12)

def client_thread(conn, addr):
    with conn:
        # image_handle, image_idx = np.zeros((32, 32), np.int8), 0
        print(f"[CONNECTION] Connection received at {addr}")

        client_name = str(addr[0]) + '_' + str(addr[1])
        if not os.path.isdir('data'):
            os.mkdir('data')
        if str(client_name) not in os.listdir('data'):
            os.mkdir('data/' + client_name)

        img_num = 0
        while True:
            print("[CONNECTION] Received Packet...")
            data = conn.recv(4096)
            print("data : ", data, len(data))
            received_data = loads(data)
            # print(received_data) this was for debugging
            print(received_data)

            print("metadata received")
            metaData=received_data[0]
            with open("data/" + client_name + "/" + str(img_num) + ".yml", 'w') as outfile:
                yaml.dump(metaData, outfile, default_flow_style=False)
            print("image received")
            # image = received_data[1]
            # pil_image = Image.fromarray(image.reshape(IMAGE_SHAPE))
            # pil_image.save("data/" + client_name + "/" + str(img_num) + ".png")
            # print("image : ", image, len(image))

            img_num += 1
    print(f"[CONNECTION] Disconnected from {addr}")


class DroneAgent:
    def __init__(self, server_addr, server_dests):
        self.server_addr = server_addr
        self.server_dests = server_dests # Read from a launch file in future
        self.pose = { # Based on ROS sensor_msgs/NatSatFix and sensor_msgs/Imu
            'header' : None,
            'gps_status': None,
            'pose': {
                'latitude': 308.19657,
                'longitue': 391.66570,
                'altitude': 109.53409
            },
            'imu': {
                'x': 1.56784,
                'y': 1.00325,
                'z': 0.67735,
                'w': 0.00000
            },
            'covariances': [0, 0, 0, 0, 0, 0, 0],
            # "updated_position": this can be calculated from coordinates when data of pose will change as written in line 52
        }


        server_dests1=[]
        for serv in self.server_dests:
            if abs(self.server_addr[2] - serv[2]) <= 1:
                print(serv[2], self.server_addr[2])
                stack_serv = (serv[0], serv[1])
                server_dests1.append(stack_serv)
        self.server_addr = (server_addr[0], server_addr[1])
        self.server_dests = server_dests1


        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.parse_server_dests()
        self.client_conns = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) for _ in self.server_dests]

        self.server.bind(self.server_addr)
        self.server.listen(5)
        print(f"[INFO] Listening on {self.server_addr[0]}:{self.server_addr[1]}")
            
        thread = threading.Thread(target=self.open_server)
        thread.start()

        thread = threading.Thread(target=self.search_for_conns)
        thread.start()

        print(f"[INFO] DroneAgent {self.server_addr[0]}:{self.server_addr[1]} finished initiating")

    def parse_server_dests(self):
        for idx, entry in enumerate(self.server_dests):
            if self.server_addr == entry:
                self.server_dests.pop(idx)
                return

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
            time.sleep(30)
                

    def spin(self):
        while True:
            # image = np.random.randint(255, size=IMAGE_SHAPE, dtype=np.uint8).tobytes() # Camera Feed
            image = np.random.randint(255, size=IMAGE_SHAPE)
            # image = dumps(image)
            # metaData=dumps(self.pose)
            metaData=self.pose
            dataList=[metaData,image]
            dataList=dumps(dataList)

            for client in self.client_conns:
                try:
                    if (client.getsockname()[0] != '0.0.0.0'):
                        print(f"[INFO] {client.getsockname()} sending image...")
                        client.send(dataList)
                except:
                    pass 
            time.sleep(10)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server-ip', default=socket.gethostbyname(socket.gethostname()), type=str)
    parser.add_argument('-p', '--server-port', default=9797, type=int)
    parser.add_argument('-d', '--server-position', default=1, type=int)  # to specify initial position of the drone
    args = parser.parse_args()

    SERVER_ADDR = (args.server_ip, args.server_port, args.server_position)

    with open('server_dests.json') as f:
        data = json.load(f)
        server_dests = [(agent["ip"], agent["port"], agent["position"]) for agent in data["info"]]  #added a initial position of server
        f.close()

    print(SERVER_ADDR[0])
    drone = DroneAgent(SERVER_ADDR, server_dests)
    drone.spin()
