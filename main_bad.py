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
from collections import deque

import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

IMAGE_SHAPE = (12, 12)
CONNECTION_LIMIT = 2 # Meters
MAX_TRANS_DIST = 20

def sort_server_dests(arr):
    """
    Bubble Sort -> Small array, low moving cost
    """
    swapped = False
    for i in range(len(arr) - 1):
        for j in range(0, len(arr) - i - 1):
            if (arr[j][1] < arr[j + 1][1]):
                swapped = True
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
        if not swapped:
            return

def check_dist(state_one, state_two):
    lat_dist = state_one["pose"]["latitude"] - state_two["pose"]["latitude"]
    long_dist = state_one["pose"]["longitude"] - state_two["pose"]["longitude"]
    alt_dist = state_one["pose"]["altitude"] - state_two["pose"]["altitude"]
    dist = np.sqrt(np.power(lat_dist, 2) + np.power(long_dist, 2) + np.power(alt_dist, 2))

    return dist

class DroneAgent:
    def __init__(self, server_addr, server_dests):
        self.server_addr = server_addr
        self.state = None
        self.server_dests = self.parse_server_dests(server_dests)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_conns = {"connections":[]}
        self.forward_queue = deque(maxlen=10)
        self.key = self.generate_key()
        
        sort_server_dests(self.server_dests)
        for ip, port, state in self.server_dests:
            self.client_conns["connections"].append({
                "conn": socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                "ip": ip,
                "port": port,
                "state": state
            })


        self.server.bind(self.server_addr)
        self.server.listen(5)
        print(f"[INFO] Listening on {self.server_addr[0]}:{self.server_addr[1]}")
            
        thread = threading.Thread(target=self.open_server)
        thread.start()

        thread = threading.Thread(target=self.search_for_conns)
        thread.start()

        print(f"[INFO] DroneAgent {self.server_addr[0]}:{self.server_addr[1]} finished initiating")

    def generate_key(self):
        password = b"password"
        salt = b"somesalt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        f = Fernet(key)
        return f

    def parse_server_dests(self, server_dests):
        out = []
        del_idx = None
        for idx, (ip, port, state) in enumerate(server_dests):
            if self.server_addr == (ip, port):
                self.state = state
                continue
            out.append((ip, port, state))
        if isinstance(del_idx, int):
            out.pop(idx)
        return out

    def open_server(self):
        while True:
            print("[INFO] Waiting to accept clients")
            conn, addr = self.server.accept()
            print(f"[INFO] Starting thread for connection {addr}")
            thread = threading.Thread(target=self.client_thread, args=(conn, addr))
            thread.start()
    
    def search_for_conns(self):
        while True: 
            # print(f"[CONNECTION] Looking for connections")
            for idx, client in enumerate(self.client_conns["connections"]):
                try:
                    ping = 1
                    client["conn"].send(ping.to_bytes(1, 'little'))
                except:
                    try:
                        if check_dist(self.state, client["state"]) <= CONNECTION_LIMIT:
                            ip, port, _ = self.server_dests[idx]
                            print(f"[CONNECTION] Searching for {ip}:{port}...")
                            client["conn"].connect((ip, port))
                            print(f"[CONNECTION] Connection made at {ip}:{port}")
                    except:
                        pass
            time.sleep(10)

    def client_thread(self, conn, addr):
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
                try:
                    data = conn.recv(4096)
                    if data == int(1).to_bytes(1, 'little'):
                        print("[CONNECTION] Ping received")
                        continue
                    else:
                        print(f"[CONNECTION] Received Packet from {addr}...")

                        request = secrets.token_hex(16)
                        encrypted_req = self.key.encrypt(request.encode())
                        conn.send(encrypted_req)
                        print("Verifying sender, sending value: ", request)
                        expected_ans = hex(int(request, 16) + int(request, 16))
                        print("The expected reply is: ", expected_ans)
                        encrypted_ans = conn.recv(1024)
                        ans = self.key.decrypt(encrypted_ans)
                        print("Received answer: ", ans.decode("ascii"))
                        if ((ans.decode("ascii")) == expected_ans):
                            print("Expected answer received")

                            data = loads(data)
                            dest, state, image = data["dest"], data["state"], data["image"]
                            if (data["dest"] == self.server_addr):
                                # Handle state
                                for client in self.client_conns["connections"]:
                                    if (client["ip"], client["port"]) is dest:
                                        client["state"] = state
                                        break
                                with open("data/" + client_name + "/" + str(img_num) + ".yml", 'w') as outfile:
                                    yaml.dump(state, outfile, default_flow_style=False)

                                # Handle image
                                pil_image = Image.fromarray(image.reshape(IMAGE_SHAPE))
                                pil_image.save("data/" + client_name + "/" + str(img_num) + ".png")
                                img_num += 1
                            else:
                                self.forward_queue.append(data)

                        else:
                            print("Wrong answer received, packet ignored")

                except: 
                    print("[ERROR] Error with conn.recv")
                
        print(f"[CONNECTION] Disconnected from {addr}")  

    def next_best(self, dest_state, data):
        """
        Greedy BFS to find shortest path -> quick
        """
        own_dist = check_dist(self.state, dest_state)
        next_best = (None, MAX_TRANS_DIST)
        for client in self.client_conns["connections"]:
            try:
                if (client["conn"].getsockname()[0] != '0.0.0.0'):
                    client_diff = check_dist(client["state"], dest_state)
                    next_best = (client["conn"], client_diff) if client_diff < next_best[1] else next_best
            except:
                pass
        

        # dest = data["dest"] # for debugging
        if own_dist > next_best[1]:
            msg = dumps(data)
            next_best[0].send(msg)
            # print(f"[INFO] Found next best for {dest[0]}:{dest[1]}")

            print("Sent packet, waiting for response")
            encrypted_req = client["conn"].recv(1024)
            request = self.key.decrypt(encrypted_req)
            print("Received response: ", request.decode("ascii"))
            ans = hex(int((request.decode("ascii")), 16) + int((request.decode("ascii")), 16))
            print("Sending answer: ", ans)
            encrypted_ans = self.key.encrypt(ans.encode())
            client["conn"].send(encrypted_ans)

        else:
            # print(f"[LOSS] No path found to {dest[0]}:{dest[1]}:!")
            pass


    def send_msg(self, client, data):        
        try:
            if (client["conn"].getsockname()[0] != '0.0.0.0'):
                data["dest"] = (client["ip"], client["port"])
                msg = dumps(data)
                client["conn"].send(msg)

                print("Sent packet, waiting for response")
                encrypted_req = client["conn"].recv(1024)
                request = self.key.decrypt(encrypted_req)
                print("Received response: ", request.decode("ascii"))
                ans = hex(int((request.decode("ascii")), 16) * int((request.decode("ascii")), 16))
                print("Sending answer: ", ans)
                encrypted_ans = self.key.encrypt(ans.encode())
                client["conn"].send(encrypted_ans)

            else:
                data["dest"] = (client["ip"], client["port"])
                dest_state = client["state"]
                self.next_best(dest_state, data)
        except:
            data["dest"] = (client["ip"], client["port"])
            dest_state = client["state"]
            self.next_best(dest_state, data)
           

    def spin(self):
        while True:
            # image = np.random.randint(255, size=IMAGE_SHAPE, dtype=np.uint8).tobytes() # Camera Feed
            image = np.random.randint(255, size=IMAGE_SHAPE, dtype=np.uint8) # Camera Feed
            data = {
                "dest" : (None, None),
                "state" : self.state,
                "image": image
            }

            for data in self.forward_queue:
                client = None
                for entry in self.client_conns["connections"]:
                    if data["dest"] == (entry["ip"], entry["port"]):
                        client = entry
                        break
                
                if client is not None:
                    self.send_msg(client, data)
                else:
                    continue
            self.forward_queue.clear()

            for client in self.client_conns["connections"]:
                print("Sending msg")
                self.send_msg(client, data)

            time.sleep(5)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server-ip', default=socket.gethostbyname(socket.gethostname()), type=str)
    parser.add_argument('-p', '--server-port', default=9797, type=int)
    args = parser.parse_args()

    SERVER_ADDR = (args.server_ip, args.server_port)
    
    with open('server_dests.json') as f:
        data = json.load(f)
        server_dests = [(agent["ip"], agent["port"], agent["state"]) for agent in data["info"]]
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