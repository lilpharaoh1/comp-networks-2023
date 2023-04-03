import random
import socket
import time
import numpy as np
import threading
import argparse
import os
import json
# from PIL import Image
from pickle import dumps, loads
import yaml
from collections import deque

import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

IMAGE_SHAPE = (12, 12)
CONNECTION_LIMIT = 2  # Meters
MAX_TRANS_DIST = 20
ACK_TIMER = 20


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
        self.client_conns = {"connections": []}
        self.forward_queue = deque(maxlen=10)
        self.key = self.generate_key()
        self.ack_queue = deque(maxlen=10)
        self.ack_trace = {}

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
        backend = default_backend()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
            backend=backend
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
                    print(f"[CONNECTION] Sending ping to {client['ip']}:{client['port']}")
                    client["conn"].send(ping.to_bytes(1, 'little'))
                except:
                    try:
                        if check_dist(self.state, client["state"]) <= CONNECTION_LIMIT:
                            print(f"[CONNECTION] Searching for {client['ip']}:{client['port']}...")
                            client["conn"].connect((client['ip'], client['port']))
                            print(f"[CONNECTION] Connection made at {ip}:{port}")
                    except:
                        pass
            time.sleep(10)

    def client_thread(self, conn, addr):
        with conn:
            # image_handle, image_idx = np.zeros((32, 32), np.int8), 0
            print(f"[CONNECTION] Connection received at {addr}")

            client_name = str(addr[0]) + '_' + str(addr[1])# i beleive this shouldnot be changes bcz it represents one connection so should be this only
            if not os.path.isdir('data'):
                os.mkdir('data')
            if str(client_name) not in os.listdir('data'):
                os.mkdir('data/' + client_name)
            key = self.generate_key()
            while True:
                try:
                    data = conn.recv(4096)
                    if data == int(1).to_bytes(1, 'little'):
                        #print("[CONNECTION] Ping received")
                        continue
                    else:
                        print(f"[CONNECTION] Received Packet from {addr}...")

                        # request = secrets.token_hex(16)
                        # encrypted_req = key.encrypt(request.encode())
                        # conn.send(encrypted_req)
                        # print("Verifying sender, sending value: ", request)
                        # expected_ans = hex(int(request, 16) + int(request, 16))
                        # print("The expected reply is: ", expected_ans)
                        # encrypted_ans = conn.recv(1024)
                        # print("Encrypted Ans : ", encrypted_ans)
                        # try:
                        #     print(ans)
                        #     ans = key.decrypt(encrypted_ans)
                        # except:
                        #     print("decrypt error")
                        #     break
                        # print("Received answer: ", ans.decode("ascii"))
                        # if ((ans.decode("ascii")) == expected_ans):
                        #     print("Expected answer received")

                        data = loads(data)
                        source, dest, ack, img_num, state, image = data["source"], data["dest"], data["ACK"], data["image_seq"], data["state"], data["image"]
                        if ack:
                            print("[ACK] Received ACK...")
                            self.ack_trace.pop(img_num)
                            continue
                        if (data["dest"] == self.server_addr):
                            # Handle state
                            for client in self.client_conns["connections"]:
                                if (client["ip"], client["port"]) is dest:
                                    client["state"] = state
                                    break
                            with open("data/" + client_name + "/" + str(source[1]) + "_" + str(img_num) + ".yml",
                                        'w') as outfile:
                                yaml.dump(state, outfile, default_flow_style=False)

                            # Handle image
                            save_name = "data/" + client_name + "/" + str(source[1]) + "_" + str(img_num) + ".png"
                            np.save(save_name, image)
                            tmp = data["source"]
                            data["source"] = data["dest"]
                            data["dest"] = tmp
                            data["ACK"] = True
                            self.ack_queue.append(data)
                        else:
                            self.forward_queue.append(data)
                        # else:
                        #     print("Malicious")

                except:
                    print("[ERROR] Error with conn.recv")
                    break
        print(f"[CONNECTION] Disconnected from {addr}")  


    def next_best(self, dest_state, data):
        """
        Greedy BFS to find shortest path -> quick
        """
        own_dist = check_dist(self.state, dest_state)
        finalclient = None
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
            try:
                next_best[0].send(msg)
                register_send_msg(next_best[0], msg)
                finalclient = next_best[0]
            except:
                # print("[ROUTING] Next best not connected")
                # print(f"[ROUTING] Found next best for {dest[0]}:{dest[1]}")
                pass
        else:
            # print(f"[ROUTING] No path found to {dest[0]}:{dest[1]}:!")
            pass

        return finalclient

    def send_msg(self, client, data):
        finalclient = None

        try:
            if (client["conn"].getsockname()[0] != '0.0.0.0'):
                data["dest"] = (client["ip"], client["port"])
                msg = dumps(data)
                client["conn"].send(msg)
                self.register_send_msg(client, data)
                finalclient = client["conn"]
            else:
                data["dest"] = (client["ip"], client["port"])
                dest_state = client["state"]
                finalclient = self.next_best(dest_state, data)
        except:
            data["dest"] = (client["ip"], client["port"])
            dest_state = client["state"]
            finalclient = self.next_best(dest_state, data)

        return finalclient

    def waitACK(self, key):
        while (1):
            time.sleep(ACK_TIMER)
            try:
                self.ack_trace[key][2] = 1
            except:
                return

    def register_send_msg(self,client,data):
        key = data['image_seq']
        self.ack_trace[key] = [client, data, 0]
        thread = threading.Thread(target=self.waitACK, args=(key,))
        thread.start()


    def spin(self):
        while True:
            # image = np.random.randint(255, size=IMAGE_SHAPE, dtype=np.uint8).tobytes() # Camera Feed
            image = np.random.randint(255, size=IMAGE_SHAPE, dtype=np.uint8)  # Camera Feed
            img = ''.join(random.choice('0123456789abcdef') for i in range(16))
            data = {
                "source": self.server_addr , 
                "dest": (None, None),
                "ACK":  False,
                "image_seq": img,   
                "state": self.state,
                "image": image
            }

            for ack_data in self.ack_queue:
                client = None
                for entry in self.client_conns["connections"]:
                    if ack_data["dest"] == (entry["ip"], entry["port"]):
                        client = entry
                        break

                if client is not None:
                    conn = self.send_msg(client, ack_data)
            self.ack_queue.clear()    

            for forward_data in self.forward_queue:
                client = None
                for entry in self.client_conns["connections"]:
                    if forward_data["dest"] == (entry["ip"], entry["port"]):
                        client = entry
                        break

                if client is not None:
                    conn = self.send_msg(client, forward_data)
                    self.register_send_msg(client, forward_data)
            self.forward_queue.clear()

            for client in self.client_conns["connections"]:
                conn = self.send_msg(client, data)
                # self.register_send_msg(client, data)

            for ack in self.ack_trace:
                if self.ack_trace[ack][2]:
                    client = self.ack_trace[ack][0]
                    data = self.ack_trace[ack][1]
                    # print("ACK Retrasnmit ", data)
                    print(f"[ACK] Retransmitting to {data['dest'][0]}:{data['dest'][1]}")
                    conn = self.send_msg(client, data)
                    self.ack_trace[ack][2] = 0

            time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server-ip', default=socket.gethostbyname(socket.gethostname()), type=str)
    parser.add_argument('-p', '--server-port', default=33206, type=int)
    args = parser.parse_args()

    SERVER_ADDR = (args.server_ip, args.server_port)

    
    with open('rasp-test.json') as f:
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
