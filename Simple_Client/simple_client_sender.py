import socket
import sys

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('127.0.0.1', 55688)
    sock.connect(server_address)
    sock.send('ADD_pythonSender')
    
        
