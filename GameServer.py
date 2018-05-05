from twisted.internet import protocol, reactor, endpoints, tksupport, defer
from twisted.internet.task import deferLater
from bidict import bidict
from datetime import datetime
import json
import os
import traceback


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
            log = '[' + datetime.now().strftime("%H:%M:%S") + '] ' + \
                'get: ' + repr(data) + ' from ' + my_addr
        else:
            log = '[' + datetime.now().strftime("%H:%M:%S") + '] ' + \
                'get: ' + repr(data) + ' from ' + self.tag
        print log
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
            print '[' + datetime.now().strftime("%H:%M:%S") + '] ' + \
                my_name + ' lost connection'


class EchoFactory(protocol.Factory):

    def buildProtocol(self, addr):
        log = '[' + datetime.now().strftime("%H:%M:%S") + '] ' + \
            "new device from " + addr.host
        print log
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
            if(msg == 'UPDATE_CONFIG'):

            temp_tag = self.findTag(echo, msg)
            if(temp_tag != ''):
                echo.tag = temp_tag
                msg_array.remove(msg)
        networkGroup.forwardMessageSequence(echo.tag, msg_array)

    def findTag(self, echo, data):
        # Find if the message contaions any tag
        for tag in self.device_tags:
            if("ADD_" + tag in data):
                log = '[' + datetime.now().strftime("%H:%M:%S") + \
                    '] ' + 'get device: ' + tag
                print log
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
            print 'no such event or source'
        except:
            traceback.print_exc()
        return ''

    def sendToObserver(self, msg):
        for observer in self.observers:
            observer.transport.write(msg + '\n')

    def sendToTarget(self, target_tag, msg):
        if(target_tag in self.tag_echo_table.keys()):
            log = '[' + datetime.now().strftime("%H:%M:%S") + '] ' + \
                "send " + repr(msg) + " to " + target_tag
            print log
            target_tranport = self.tag_echo_table[target_tag].transport
            target_tranport.write(msg + '\n')
        else:
            log = '[' + datetime.now().strftime("%H:%M:%S") + '] ' + \
                "target " + target_tag + " not online."
            print log


roomConfig = json.load(open("RoomConfig.json"))
routing = roomConfig["routing"]
childDevices = roomConfig["childDevices"]
default_states = roomConfig["gameStates"]

gameStates = GameState(default_states)
networkGroup = NetworkGroup(childDevices)
networkGroup.server_online = True
reactor.listenTCP(55688, EchoFactory())
print '[' + datetime.now().strftime("%H:%M:%S") + '] ' + "start the server"
reactor.run()
