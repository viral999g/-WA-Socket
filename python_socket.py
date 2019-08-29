#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
# from utilities import *
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import traceback, json, time, os, sys, pymongo
from Crypto import Random
import binascii
from Crypto import Random

sys.dont_write_bytecode = True
# reload(sys)
# sys.setdefaultencoding("utf-8")
clientInstances = {}

files_dir = "/home/bharat/Downloads/WA_socket/client_files/"

MYCLIENT = pymongo.MongoClient("mongodb://localhost:27017/",
                            connect=False)

MYDB = MYCLIENT['wa']
GROUPSCOLL = MYDB['groups']


class WhatsAppWeb(WebSocket):
    client_remoteJid = None
    client_file = None
    client_tempfile = None
    def sendJSON(self, obj, tag):
        self.sendMessage("['" + tag + "'," + json.dumps(obj) + "]")

    def sendError(self, reason, tag):
        print("sending error: " + reason)
        self.sendJSON({"type": "error", "reason": reason}, "error")

    def sendToReceiver(self, receiverJid, message):
        message = "{'add': 'relay'}," + json.dumps(message)
        if receiverJid in clientInstances:
            clientInstances[receiverJid].sendJSON(message, "action")

        self.appendToFile(receiverJid, message, "action")

    def sendToReceiverJson(self, receiverJid, message, tag):
        message = "{'add': 'relay'}," + json.dumps(message)

        if receiverJid in clientInstances:
            clientInstances[receiverJid].sendJSON(message, tag)

        self.appendToFile(receiverJid, message, tag)
    
    def appendToFile(self,receiverJid, message, tag):
        file = open(files_dir + receiverJid + ".txt", "a+")
        file.write("," + "['" + tag + "'," + str(message) + "]")

    def sendMessageReceipt(self, from_client, to_client, flag, message_id, participant):
        message_json = {
            "from" : from_client,
            "ack" : flag,
            "cmd" : "ack",
            "to" : to_client,
            "t" : int(time.time()),
            "id" : message_id
        }

        clientInstances[from_client].sendJSON(message_json, "Msg")
        self.appendToFile(from_client, message_json, "Msg")

    def sendMessageReceiptData(self, data, tag):
        from_client = self.get_number(data["from"])
        clientInstances[from_client].sendJSON(data, tag)
        self.appendToFile(from_client, data, tag)

    def get_number(self, jid):
        at_the_rate_index = jid.find("@")
        return jid[0:at_the_rate_index]

    def send_encryption_key_message(self, gjid, participant):
        encryption_key_message = [
            {
                "add" : "relay"
            },
            [
            {
                "key" :
                {
                    "fromMe" : True,
                    "id" : str(binascii.hexlify(Random.get_random_bytes(8)).upper().decode("utf-8")),
                    "remoteJid" : gjid
                }
                ,
                "messageStubType" : "E2E_ENCRYPTED",
                "messageTimestamp" : str(int(time.time()))
            }
            ]
        ]

        self.sendToReceiverJson(participant, encryption_key_message[1], "action")

    def send_group_create_action_message(self, gjid, participant, creator):
        group_create_action_message = [
            {
                "add" : "relay"
            },
            [
            {
                "key" :
                {
                    "fromMe" : True,
                    "id" : str(binascii.hexlify(Random.get_random_bytes(8)).upper().decode("utf-8")),
                    "remoteJid" : gjid
                }
                ,
                "messageStubType" : "GROUP_CREATE",
                "messageTimestamp" : str(int(time.time())),
                "participant" : self.get_number(creator) + "@s.whatsapp.net"
            }
            ]
        ]

        self.sendToReceiverJson(participant, group_create_action_message[1], "action")
        


    def add_members_in_group(self, gjid, participants, receivers, adder):
        add_member_message =[
            {
                "add" : "relay"
            },
            [
                {
                    "key" :
                    {
                        "fromMe" : True,
                        "id" : str(binascii.hexlify(Random.get_random_bytes(8)).upper().decode("utf-8")),
                        "remoteJid" : gjid
                    }
                    ,
                    "messageStubParameters" : participants
                    ,
                    "messageStubType" : "GROUP_PARTICIPANT_ADD",
                    "messageTimestamp" : str(int(time.time())),
                    "participant" : adder
                }
            ]
        ]

        for r in receivers:
            self.sendToReceiverJson(r, add_member_message[1], "action")


    def create_new_group(self, request):
        imp_data = request[1]['data']
        creator = imp_data[1]
        gjid = request[1]['id']
        group_data = imp_data[2]
        creation_ts = group_data['creation']

        admins = group_data['admins']
        super_admins = group_data['superadmins']
        regulars = group_data['regulars']
        subject = group_data['subject']

        participants = []
        for participant in regulars:
            level = 0
            participants.append([self.get_number(participant), level])

        for participant in super_admins:
            level = 2
            participants.append([self.get_number(participant), level])                   
    
        GROUPSCOLL.insert({"gjid": gjid, "subject": subject, "participants": participants, "creator": self.get_number(creator), "creation_ts": creation_ts, "admins": admins, "superadmins": super_admins, "icon": "", "group_desc": "", "invite_url": "", "flag_group_info": 0, "flag_send_messages": 0})

        

       

        request.pop(0)
        for participant in participants:
            self.send_encryption_key_message(gjid, participant[0])
            self.sendToReceiverJson(participant[0], request, "Chat")
            self.send_group_create_action_message(gjid, participant[0], creator)
            if participant[0] != self.get_number(creator):
                self.add_members_in_group(gjid, [participant[0] + "@s.whatsapp.net"], [participant[0]], self.get_number(creator) + "@s.whatsapp.net")

    def add_members_in_group_process(self, request):
        imp_data = request[1]['data']
        adder = imp_data[1]
        gjid = request[1]['id']

        get_group_info = GROUPSCOLL.find_one({"gjid": gjid})
        if get_group_info != None and adder in get_group_info['admins']:
            creator = get_group_info['creator']
            participants_added = imp_data[2]['participants']
            participants = []
            for p in participants_added:
                participant_arr = [self.get_number(p), 0]
                participants.append(participant_arr)
                GROUPSCOLL.update({"gjid": gjid}, {"$push": {"participants": participant_arr}})
            request.pop(0)
            for participant in participants:
                self.send_encryption_key_message(gjid, participant[0])
                self.sendNewGroupToReceiver(participant[0], adder, gjid, "Chat")
                self.send_group_create_action_message(gjid, participant[0], creator)
                if participant[0] != self.get_number(creator):
                    self.add_members_in_group(gjid, [participant[0] + "@s.whatsapp.net"], [participant[0]], self.get_number(creator) + "@s.whatsapp.net")

    def sendNewGroupToReceiver(self, participant, adder,gjid, tag):
        group_info = GROUPSCOLL.find_one({"gjid": gjid})
        regulars = []
        for p in group_info['participants']:
            if p[1] == 1:
                regulars.append(p[0] + "@c.us")

        message_body = [
        "Chat",
            {
            "cmd" : "action",
            "data" :
            [
                "introduce",
                adder,
                {
                    "admins" :group_info['admins'],
                    "creation" : group_info['creation_ts'],
                    "desc" : group_info['group_desc'],
                    "descId" : "",
                    "descOwner" : "",
                    "descTime" : None,
                    "regulars" : regulars,
                    "s_o" :  group_info['creator'] + "@c.us",
                    "s_t" : group_info['creation_ts'],
                    "subject" : group_info['subject'],
                    "superadmins" : group_info['superadmins']
                }
            ]
            ,
            "id" : gjid
            }
        ]

        self.sendToReceiverJson(participant, message_body, "Chat")

    def handleMessage(self):
        try:
            request = json.loads(self.data)
            if request[0] == "auth":
                if request[1]['type'] == "new":
                    temp_client_remoteJid = request[2]['remoteJid']
                    self.client_remoteJid = self.get_number(temp_client_remoteJid)
                    self.client_file = files_dir + self.client_remoteJid + ".txt"
                    self.client_tempfile = files_dir + self.client_remoteJid + "_temp.txt"
                    print(os.path.isfile(self.client_file))
                    if os.path.isfile(self.client_file) == True:
                        os.system("mv " + self.client_file + " " + self.client_tempfile)

                        f = open(self.client_tempfile, "r")
                        l = "[[]" + str(f.read()).replace("\n", "") + "]"
                        print(l)
                        os.system("rm " + self.client_tempfile)

                    else:
                        l = ""

                    clientInstances[self.client_remoteJid] = self
                    self.sendJSON({"status": "success"}, "auth")
                    self.sendJSON({"data": l}, "q")

            elif request[0] == "action" and request[1]['add'] == "relay":
                send_to = request
                send_to = send_to[2]
                print(send_to)
                send_to[0]["key"]["fromMe"] = False
                send_to[0]["messageTimestamp"] = str(int(time.time()))
                message_id = send_to[0]["key"]["id"]

                receiverJid = send_to[0]["key"]["remoteJid"]
                if "@s.whatsapp.com" in receiverJid:
                    send_to[0]["key"]["remoteJid"] = self.client_remoteJid + "@s.whatsapp.com"
                    receiver_number = self.get_number(receiverJid)


                    self.sendToReceiver(receiver_number, send_to)
                    self.sendMessageReceipt(self.client_remoteJid, receiver_number, 1, message_id, "")
                elif "@g.us" in receiverJid:
                    send_to[0]["participant"] = self.client_remoteJid + "@s.whatsapp.net"
                    participants = GROUPSCOLL.find_one({"gjid": receiverJid})["participants"]
                    if [self.client_remoteJid, 0] in participants or [self.client_remoteJid, 1] in participants or [self.client_remoteJid, 2] in participants:
                        for p in participants:
                            if p[0] != self.client_remoteJid:
                                self.sendToReceiver(p[0], send_to)

                        self.sendMessageReceipt(self.client_remoteJid, receiverJid, 1, message_id, "")

            elif request[0] == "Msg" or request[0] == "MsgInfo" and request[1]['cmd'] == 'ack':
                send_to = request[1]
                self.sendMessageReceiptData(send_to, request[0])


            elif request[0] == "Chat" and request[1]['cmd'] == 'action' and request[1]['data'][0] == 'create':
               self.create_new_group(request) 

            elif request[0] == "Chat" and request[1]['cmd'] == 'action' and request[1]['data'][0] == 'add':
               self.add_member_in_group(request)



                    
                

        except:
            print(traceback.format_exc())

    def handleConnected(self):
        self.sendJSON({"from": "backend", "type": "connected"}, "connected")
        # for client in self.server.connections.itervalues():
        #     print(client)
        print(self.address, "connected to backend")

    def handleClose(self):
        whatsapp.disconnect()
        print(self.address, "closed connection to backend")


server = SimpleWebSocketServer("", 9011, WhatsAppWeb)
print("whatsapp-web-backend listening on port 9011")
server.serveforever()
