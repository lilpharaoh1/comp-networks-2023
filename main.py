import socket
import time 
import numpy as np
import threading
import argparse
import os
import json
from PIL import Image
from pickle import dumps, loads

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
            image = loads(data)
            print("image : ", image, len(image))
            pil_image = Image.fromarray(image.reshape(IMAGE_SHAPE))
            pil_image.save("data/" + client_name + "/" + str(img_num) + ".png")
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
            'covariances': [0, 0, 0, 0, 0, 0, 0]
        }
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
            image = dumps(image)

            ## Make the .yaml file
            ## file = self.pose information

            for client in self.client_conns:
                try:
                    if (client.getsockname()[0] != '0.0.0.0'):
                        print(f"[INFO] {client.getsockname()} sending image...")
                        client.send(image)
                except:
                    pass 
            time.sleep(10)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server-ip', default=socket.gethostbyname(socket.gethostname()), type=str)
    parser.add_argument('-p', '--server-port', default=9797, type=int)
    args = parser.parse_args()

    SERVER_ADDR = (args.server_ip, args.server_port)
    
    with open('server_dests.json') as f:
        data = json.load(f)
        server_dests = [(agent["ip"], agent["port"]) for agent in data["info"]]
        f.close()

    print(SERVER_ADDR[0])
    drone = DroneAgent(SERVER_ADDR, server_dests)
    drone.spin()




#     rosbag2_bagfile_information:
#   version: 4
#   storage_identifier: sqlite3
#   relative_file_paths:
#     - real-stat-odom.db3
#   duration:
#     nanoseconds: 43998124512
#   starting_time:
#     nanoseconds_since_epoch: 1657209849978848788
#   message_count: 4403
#   topics_with_message_count:
#     - topic_metadata:
#         name: /ros_can/twist
#         type: geometry_msgs/msg/TwistWithCovarianceStamped
#         serialization_format: cdr
#         offered_qos_profiles: "- history: 1\n  depth: 1\n  reliability: 1\n  durability: 2\n  deadline:\n    sec: 9223372036\n    nsec: 854775807\n  lifespan:\n    sec: 9223372036\n    nsec: 854775807\n  liveliness: 1\n  liveliness_lease_duration:\n    sec: 9223372036\n    nsec: 854775807\n  avoid_ros_namespace_conventions: false"
#       message_count: 4403
#   compression_format: ""
#   compression_mode: ""