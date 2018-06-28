import socket
import sys
import time

running = True
scheduled_command = []


def splitMsg(data, spliter):
    msg_array = data.split(spliter)
    msg_array_sorted = filter(None, msg_array)
    return msg_array_sorted

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', 55688)
    sock.connect(server_address)
    sock.setblocking(0)
    sock.send('ADD_Scheduler')
    print 'start runing'
    while(running):
        try:
            try:
                message = sock.recv(1024)
            except socket.error, e:
                message = ""
            message = message.replace("\n", "")
            for msg in splitMsg(message, ','):
                msgpair = splitMsg(msg, '_')
                if(len(msgpair) == 2):
                    try:
                        delaytime = float(msgpair[1])
                    except:
                        delaytime = 0
                    scheduled_command.append((
                        msgpair[0], time.time() + delaytime))
        except KeyboardInterrupt:
            running = False
            sock.close()
        for event in scheduled_command:
            if(time.time() > event[1]):
                cmd = event[0] + '\n'
                print 'send ' + cmd
                sock.send(cmd)
                try:
                    scheduled_command.remove(event)
                except:
                    print 'del problem'
