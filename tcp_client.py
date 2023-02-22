import socket
import time
import numpy as np

SERVER = "192.168.56.1"
PORT = 9797

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER, PORT))

# file = open('aerial_sample.jpg', 'rb')
# image = file.read(2048)
i = 0
image = np.random.normal(size=(1024,1024)).tobytes()

while (i < 10):
    client.send(image)
    time.sleep(4)
    i += 1

client.shutdown(1)
client.close()