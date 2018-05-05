from twisted.internet import protocol, reactor, endpoints, tksupport, defer
from twisted.internet.task import deferLater
from bidict import bidict
from Tkinter import *
from datetime import datetime

'''

Network Member:
unity game , tag = UNT , u
calibrator , tag = CAL , c
platform   , tag = PLT , p
celling    , tag = CLC , e
blackboard , tag = BKB , k
bulletin   , tag = BLT , b
wall       , tag = WAL , w
lightwall  , tag = LCW , l
waord_recog, tag = WRD , r
central    , tag = CTR , n
observer   , tag = OBC , o


'''

tags_table={'u':'UNT','c':'CAL','p':'PLT','e':'CLC', 'n':'CTR',
            'k':'BKB','b':'BLT','w':'WAL','l':'LCW', 'r':'WRD',
            'o':'OBB','t':'OBT'}


class Echo(protocol.Protocol,object):
    def __init__(self):
        super(Echo,self).__init__()
        self.tag = ''
        
    def dataReceived(self, data):
        my_addr = self.transport.getPeer().host
        log = ''
        if(self.tag == ''):
            log = '[' + datetime.now().strftime("%H:%M:%S")+ '] ' + 'get: ' + repr(data) + ' from ' + my_addr
        else:
            log = '[' + datetime.now().strftime("%H:%M:%S")+ '] ' + 'get: ' + repr(data) + ' from ' + self.tag
        Observer.addLog(log)
        if(data.find('OKACK')>=0 and self.tag != '' ):
            NG.sendToObserver('RESETACK'+self.tag)
        if(data.find('ACK') < 0 and self.tag != '' and 'OB' not in self.tag ):
            NG.sendToObserver('GETDATA' + data + 'FROM' + self.tag)
        #Split the received data into array
        msg_array = data.split(',')
        msg_array_sorted = filter(None,msg_array)
        for msg in msg_array_sorted:
            temp_tag = NG.findTag(msg,self)
            if(temp_tag != ''):
                self.tag = temp_tag
                msg_array_sorted.remove(msg)
        NG.forwardMessageSequence(msg_array_sorted)
        
    def connectionLost(self,reason):
        my_name = self.tag
        if (NG.server_online):
            my_name = ''
            if(self.tag == ''):
                my_name = self.transport.getPeer().host
                print '[' + datetime.now().strftime("%H:%M:%S")+ '] '+my_name + ' lost connection'
            else:
                my_name = self.tag
                Observer.updateState(self.tag,False)
            print '[' + datetime.now().strftime("%H:%M:%S")+ '] '+my_name + ' lost connection'
        

class EchoFactory(protocol.Factory):
    def buildProtocol(self, addr):
        log = '[' + datetime.now().strftime("%H:%M:%S")+ '] ' + "new client from "+ addr.host
        Observer.addLog(log)
        echo = Echo()
        NG.member[addr.host] = echo
        return echo

class NetworkGroup():
    def __init__(self,table):
        self.member=dict()
        self.tag_echo_table=dict()
        self.tag_addr_table=bidict()
        self.member_tags = table.values()
        self.header_tag_table = table
        self.msg_buffer = list()
        self.server_online = False

    def findTag(self,data,my_echo):
        #Find if the message contaions any tag
        for tag in self.member_tags:
            if("ADD" + tag in data):
                log = '[' + datetime.now().strftime("%H:%M:%S")+ '] ' + 'get member: '+tag
                Observer.addLog(log)
                self.tag_echo_table[tag] = my_echo
                Observer.updateState(tag,True)
                return tag
        return ''
    def forwardMessageSequence(self,msg_seq_list):
        seq_dict = dict()
        for msg in msg_seq_list:
            if msg[0] in seq_dict.keys():
                seq_dict[msg[0]] += ','+msg[1:]
            else:
                seq_dict[msg[0]] = msg[1:]
        for i in range(len(seq_dict)):
            header = seq_dict.keys()[i]
            target_tag = self.analyzeTargetTag(header)
            if (target_tag==''):
                return
            self.sendToTarget(seq_dict[header],target_tag)
    def analyzeTargetTag(self,data):
        header = data[0]
        if(header not in self.header_tag_table.keys()):
            return ''
        target_tag = self.header_tag_table.get(header, '')
        #If can't find matching target, send to unity anyway.
        return target_tag
    def sendToObserver(self,msg):
        if('OBB' in self.tag_echo_table.keys()):
            target_tranport = self.tag_echo_table['OBB'].transport
            target_tranport.write(msg + '\n')
        if('OBT' in self.tag_echo_table.keys()):
            target_tranport = self.tag_echo_table['OBT'].transport
            target_tranport.write(msg + '\n')
        
    def sendToTarget(self,msg,target_tag):
        if(target_tag in self.tag_echo_table.keys()):
            target_tranport = self.tag_echo_table[target_tag].transport
            log = '[' + datetime.now().strftime("%H:%M:%S")+ '] ' + "send "+ repr(msg) +" to "+target_tag 
            Observer.addLog(log)
            if(target_tag == 'UNT'):
                msg += "\n"
            target_tranport.write(msg)
        else:
            log = '[' + datetime.now().strftime("%H:%M:%S")+ '] ' + "target "+target_tag+" not online."
            Observer.addLog(log)

                
class OBUI():
    def __init__(self,master,table):
        self.tags = table.values()
        self.states = []
        self.entrys = []
        for i in range(len(table)):
            Label(master, text=self.tags[i]).grid(row=i, sticky=E)
            l = Label(master, background='red' , text='Off-line')
            l.grid(row=i, column=1)
            self.states.append(l)
            e = Entry(master)
            e.grid(row=i, column=2)
            self.entrys.append(e)
            def buildButton(j):
                Button(master, text='Send', command = lambda :self.sendToMember(j)).grid(row=i, column=3)
            buildButton(i)
        self.log = Label(master, text = 'server is ready')
        self.log.grid(row=len(table), columnspan = 4)
        Button(master, text='Stop Server', command = self.closeServer).grid(row=len(table)+1, columnspan = 4)

    def changeEntryText(self,index,text):
        self.entrys[index].delete(0,END)
        self.entrys[index].insert(0,text)

    def sendToMember(self,index):
        target_tag = self.tags[index]
        data = self.entrys[index].get()
        NG.sendToTarget(data,target_tag)

    def updateState(self,tag,state):
       
        index = self.tags.index(tag)
        if(state == True):
            self.states[index].config(text='On-line', background='green')
        else:
            self.states[index].config(text='Off-line', background='red')
    def addLog(self, content):
        NG.sendToObserver(content)
        print content
        #self.log.config(text = content)
    def closeServer(self):
        NG.server_online = False
        root.destroy()
        reactor.stop()
        
        


root = Tk()
Observer = OBUI(root,tags_table)
tksupport.install(root)
NG = NetworkGroup(tags_table)
NG.server_online = True
#endpoints.serverFromString(reactor, "tcp:55688").listen(EchoFactory())
reactor.listenTCP(55688,EchoFactory())
print '[' + datetime.now().strftime("%H:%M:%S")+ '] ' + "start the server"
reactor.run()
