from twisted.internet import protocol, reactor, endpoints, tksupport, defer
from twisted.internet.task import deferLater
from Tkinter import *
import json
import os
import traceback
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    handlers=[logging.FileHandler('serverConfig.txt', 'w', 'utf-8'), ])

logger1 = logging.getLogger('echo')
logger2 = logging.getLogger('routing')


class GameState():

    def __init__(self, default_states):
        self.states = default_states

    def updateState(self, state, value):
        self.states[state] = value

    def CheckState(self, state, value):
        if(state in self.states.keys() and self.states[state] == value):
            return True
        else:
            return False


class Echo(protocol.Protocol, object):

    def __init__(self):
        super(Echo, self).__init__()
        self.tag = ''

    def dataReceived(self, data):
        my_addr = self.transport.getPeer().host
        log = ''
        if(self.tag == ''):
            log = 'get: ' + repr(data) + ' from ' + my_addr

        else:
            log = 'get: ' + repr(data) + ' from ' + self.tag

        logger1.info(log)
        # Split the received data into array
        msg_array = data.split(',')
        msg_array_sorted = filter(None, msg_array)
        networkGroup.processMsg(self, msg_array_sorted)

    def connectionLost(self, reason):
        if (networkGroup.server_online):
            my_name = ''
            if(self.tag == ''):
                my_name = self.transport.getPeer().host
            else:
                my_name = self.tag
            logger1.info(my_name + ' lost connection')


class EchoFactory(protocol.Factory):

    def buildProtocol(self, addr):
        log = "new device from " + addr.host
        logger1.info(log)
        echo = Echo()
        networkGroup.members[addr.host] = echo
        return echo


class NetworkGroup():

    def __init__(self, device_list):
        self.members = dict()
        self.tag_echo_table = dict()
        self.observer_echos = list()
        self.device_tags = device_list
        self.server_online = False

    def processMsg(self, echo, msg_array):
        for msg in msg_array:
            temp_tag = self.findTag(echo, msg)
            if(temp_tag != ''):
                echo.tag = temp_tag
                msg_array.remove(msg)
        networkGroup.forwardMessageSequence(echo.tag, msg_array)

    def findTag(self, echo, data):
        # Find if the message contaions any tag
        for tag in self.device_tags:
            if("ADD_" + tag in data):
                log = 'get device: ' + tag
                logger2.info(log)
                self.tag_echo_table[tag] = echo
                return tag
        return ''

    def forwardMessageSequence(self, source_tag, msg_seq_list):
        seq_dict = dict()
        for msg in msg_seq_list:
            action = self.analyzeEvent(source_tag, msg)
            if(action != ''):
                for target in action.keys():
                    if(target in seq_dict.keys()):
                        seq_dict[target] += action[target] + ','
                    else:
                        seq_dict[target] = action[target] + ','
        for i in range(len(seq_dict)):
            self.sendToTarget(seq_dict.keys()[i], str(seq_dict.values()[i]))

    def analyzeEvent(self, source_tag, msg):
        # look up the routing table for target device
        try:
            actions = routing[source_tag][msg]
            for action in actions:
                satisfy_rqr = True
                for rqr in action['requireState'].keys():
                    if(gameStates.CheckState(rqr, action['requireState'][rqr]) is False):
                        satisfy_rqr = False
                if(satisfy_rqr):
                    for upd in action['updateState'].keys():
                        gameStates.updateState(upd, action['updateState'][upd])
                    return action['action']
                else:
                    continue
        except KeyError:
            logger2.info('no such event or source')
        except:
            traceback.print_exc()
        return ''

    def sendToObserver(self, msg):
        for observer in self.observers:
            observer.transport.write(msg + '\n')

    def sendToTarget(self, target_tag, msg):
        if(target_tag in self.tag_echo_table.keys()):
            log = "send " + repr(msg) + " to " + target_tag
            logger2.info(log)
            target_tranport = self.tag_echo_table[target_tag].transport
            target_tranport.write(msg + '\n')
        else:
            log = "target " + target_tag + " not online."
            logger2.info(log)


class OBUI():

    def __init__(self, master, table):
        self.tags = table
        self.states = []
        self.entrys = []
        for i in range(len(table)):
            Label(master, text=self.tags[i]).grid(row=i, sticky=E)
            l = Label(master, background='red', text='Off-line')
            l.grid(row=i, column=1)
            self.states.append(l)
            e = Entry(master)
            e.grid(row=i, column=2)
            self.entrys.append(e)

            def buildButton(j):
                Button(master, text='Send', command=lambda: self.sendToMember(j)).grid(
                    row=i, column=3)
            buildButton(i)
        self.log = Label(master, text='server is ready')
        self.log.grid(row=len(table), columnspan=4)
        Button(master, text='Stop Server', command=self.closeServer).grid(
            row=len(table) + 1, columnspan=4)

    def sendToMember(self, index):
        target_tag = self.tags[index]
        data = self.entrys[index].get()
        networkGroup.sendToTarget(target_tag, data)

    def updateState(self, tag, state):
        index = self.tags.index(tag)
        if(state is True):
            self.states[index].config(text='On-line', background='green')
        else:
            self.states[index].config(text='Off-line', background='red')

    def closeServer(self):
        networkGroup.server_online = False
        root.destroy()
        reactor.stop()

roomConfig = json.load(open("RoomConfig.json"))
print roomConfig
routing = roomConfig["routing"]
childDevices = roomConfig["childDevices"]
default_states = roomConfig["gameStates"]

root = Tk()
Observer = OBUI(root, childDevices)
tksupport.install(root)
gameStates = GameState(default_states)
networkGroup = NetworkGroup(childDevices)
networkGroup.server_online = True
reactor.listenTCP(55688, EchoFactory())
logging.info("start the server")
reactor.run()
