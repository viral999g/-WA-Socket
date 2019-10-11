#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
# from utilities import *
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import traceback
import json
import time
import os
import sys
import pymongo
from Crypto import Random
import binascii
from Crypto import Random

sys.dont_write_bytecode = True
# reload(sys)
# sys.setdefaultencoding("utf-8")
clientInstances = {}

files_dir = "./client_files/"

MYCLIENT = pymongo.MongoClient("mongodb://localhost:27017/",
                               connect=False)

# MYCLIENT = pymongo.MongoClient("mongodb://localhost:27017/",
#                                username='candles123',
#                                password='D1}d-0oMe[Ts8f>OPcjH,aiC',
#                                authSource='admin',
#                                connect=False)

MYDB = MYCLIENT['wa']
USERSCOLL = MYDB['users']
GROUPSCOLL = MYDB['groups']


class WhatsAppWeb(WebSocket):
    client_remoteJid = None
    client_file = None
    client_tempfile = None

    def sendJSON(self, obj, tag):
        obj.insert(0, tag)
        self.sendMessage(json.dumps(obj))

    def sendError(self, reason, tag):
        print("sending error: " + reason)
        self.sendJSON([{"type": "error", "reason": reason}], "error")

    def sendToReceiver(self, receiverJid, message):
        receiverJid = self.get_number(receiverJid)
        message = [{'add': 'relay'}, message]
        if receiverJid in clientInstances:
            clientInstances[receiverJid].sendJSON(message, "action")

        self.appendToFile(receiverJid, message, "action")

    def sendToReceiverJson(self, receiverJid, message, tag):
        message2 = [{'add': 'relay'}, message]

        if receiverJid in clientInstances:
            clientInstances[receiverJid].sendJSON(message2, tag)

        self.appendToFile(receiverJid, message2, tag)

    def sendToReceiverModifiedJson(self, receiverJid, message, tag):
        message = [message]

        if receiverJid in clientInstances:
            clientInstances[receiverJid].sendJSON(message, tag)

        self.appendToFile(receiverJid, message, tag)

    def appendToFile(self, receiverJid, msg, tag):
        file = open(files_dir + receiverJid + ".txt", "a+")
        msg.insert(0, tag)
        if msg[0] == msg[1]:
            msg.pop(0)
        file.write(json.dumps(msg) + ",\n")

    def sendMessageReceipt(self, from_client, to_client, flag, message_id, participant):
        message_json = {
            "from": from_client,
            "ack": flag,
            "cmd": "ack",
            "to": to_client,
            "t": int(time.time()),
            "id": message_id
        }

        clientInstances[from_client].sendJSON([message_json], "Msg")
        self.appendToFile(from_client, [message_json], "Msg")

    def sendMessageReceiptData(self, data, tag):
        from_client = self.get_number(data["from"])
        if from_client in clientInstances:
            clientInstances[from_client].sendJSON([data], tag)
        self.appendToFile(from_client, [data], tag)

    def get_number(self, jid):
        at_the_rate_index = jid.find("@")
        return jid[0:at_the_rate_index]

    def send_encryption_key_message(self, gjid, participant):
        encryption_key_message = [
            {
                "add": "relay"
            },
            [
                {
                    "key":
                    {
                        "fromMe": True,
                        "id": str(binascii.hexlify(Random.get_random_bytes(8)).upper().decode("utf-8")),
                        "remoteJid": gjid
                    },
                    "messageStubType": "E2E_ENCRYPTED",
                    "messageTimestamp": str(int(time.time()))
                }
            ]
        ]

        self.sendToReceiverJson(self.get_number(
            participant), encryption_key_message[1], "action")

    def send_group_create_action_message(self, gjid, participant, creator):
        group_create_action_message = [
            {
                "add": "relay"
            },
            [
                {
                    "key":
                    {
                        "fromMe": True,
                        "id": str(binascii.hexlify(Random.get_random_bytes(8)).upper().decode("utf-8")),
                        "remoteJid": gjid
                    },
                    "messageStubType": "GROUP_CREATE",
                    "messageTimestamp": str(int(time.time())),
                    "participant": self.get_number(creator) + "@s.whatsapp.net"
                }
            ]
        ]

        self.sendToReceiverJson(self.get_number(
            participant), group_create_action_message[1], "action")

    def add_members_in_group(self, gjid, participants, receivers, adder):
        add_member_message = [
            {
                "add": "relay"
            },
            [
                {
                    "key":
                    {
                        "fromMe": True,
                        "id": str(binascii.hexlify(Random.get_random_bytes(8)).upper().decode("utf-8")),
                        "remoteJid": gjid
                    },
                    "messageStubParameters": participants,
                    "messageStubType": "GROUP_PARTICIPANT_ADD",
                    "messageTimestamp": str(int(time.time())),
                    "participant": adder
                }
            ]
        ]

        for r in receivers:
            self.sendToReceiverJson(self.get_number(
                r), add_member_message[1], "action")

    def create_new_group(self, request):
        print(request)
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
            participants.append(participant)

        for participant in super_admins:
            participants.append(participant)

        GROUPSCOLL.insert({"gjid": gjid, "subject": subject, "participants": participants, "creator": creator, "creation_ts": creation_ts,
                           "admins": admins, "superadmins": super_admins, "icon": "", "group_desc": "", "invite_url": "", "flag_group_info": 0, "flag_send_messages": 0})

        request.pop(0)
        for participant in participants:
            self.send_encryption_key_message(gjid, participant)
            self.sendToReceiverJson(
                self.get_number(participant), request, "Chat")
            self.send_group_create_action_message(gjid, participant, creator)
            if participant != creator:
                self.add_members_in_group(gjid, [self.get_number(participant) + "@s.whatsapp.net"], [
                                          participant], self.get_number(creator) + "@s.whatsapp.net")

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
                if p not in get_group_info['participants']:
                    participants.append(p)
                    GROUPSCOLL.update(
                        {"gjid": gjid}, {"$push": {"participants": p}})
            request.pop(0)
            for participant in participants:
                self.send_encryption_key_message(gjid, participant)
                self.sendNewGroupToReceiver(participant, adder, gjid, "Chat")
                self.send_group_create_action_message(
                    gjid, participant, creator)
                self.add_members_in_group(gjid, [self.get_number(
                    participant) + "@s.whatsapp.net"], [participant], self.get_number(adder) + "@s.whatsapp.net")

            # for a_participant in get_group_info['participants']:
            #     if a_participant not in participants:
            p_added = [self.get_number(
                i) + "@s.whatsapp.net" for i in participants]
            receivers_a = [
                p_temp for p_temp in get_group_info['participants'] if p_temp not in participants]
            self.add_members_in_group(
                gjid, p_added, receivers_a, self.get_number(adder) + "@s.whatsapp.net")

    def sendNewGroupToReceiver(self, participant, adder, gjid, tag):
        group_info = GROUPSCOLL.find_one({"gjid": gjid})

        message_body = [
            "Chat",
            {
                "cmd": "action",
                "data":
                [
                    "introduce",
                    adder,
                    {
                        "admins": group_info['admins'],
                        "creation": group_info['creation_ts'],
                        "desc": group_info['group_desc'],
                        "descId": "",
                        "descOwner": "",
                        "descTime": None,
                        "regulars": list(set(group_info['participants']) - set(group_info['admins']) - set(group_info['superadmins'])),
                        "s_o":  group_info['creator'] + "@c.us",
                        "s_t": group_info['creation_ts'],
                        "subject": group_info['subject'],
                        "superadmins": group_info['superadmins']
                    }
                ],
                "id": gjid
            }
        ]

        self.sendToReceiverModifiedJson(self.get_number(participant), message_body[1], "Chat")\


    def get_group_data(self, gjid):
        data = GROUPSCOLL.find_one({"gjid": gjid})
        participants = []
        participants_temp = []
        for s in data['superadmins']:
            participants_temp.append(s)
            participants.append(
                {"id": s, "isAdmin": True, "isSuperAdmin": True})

        for a in data['admins']:
            if a not in participants_temp:
                participants_temp.append(a)
                participants.append(
                    {"id": a, "isAdmin": True, "isSuperAdmin": False})

        for p in data['participants']:
            if p not in participants_temp:
                participants_temp.append(p)
                participants.append(
                    {"id": p, "isAdmin": False, "isSuperAdmin": False})

        response_body = [
            {
                "id": gjid,
                "owner": data['creator'],
                "subject": data['subject'],
                "creation": data['creation_ts'],
                "participants": participants,
                "subjectTime": data['creation_ts'],
                "subjectOwner": data['creator']
            }
        ]

        self.sendJSON(response_body, "GroupMetadata")
        self.appendToFile(self.client_remoteJid,
                          response_body, "GroupMetadata")
    
    def register_user(self, req):
        remote_jid = req['remoteJid']
        mobile_no = self.get_number(remote_jid)
        username_text = req['username']
        ts = int(time.time())
        profile_pic_url = req['eurl']

        username = {
            "username_text": username_text,
            "last_updated_at": ts
        }

        if profile_pic_url == '':
            profile_pic = {
                "eurl": "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png",
                "last_updated_at": ts
            }
        else:
            profile_pic = {
                "eurl": profile_pic_url,
                "last_updated_at": ts
            }

        status = {
            "text": "Available",
            "last_updated_ts": ts
        }

        user_obj = {}
        user_obj['remote_jid'] = remote_jid
        user_obj['mobile_no'] = mobile_no
        user_obj['username'] = username
        user_obj['created_at'] = ts
        user_obj['profile_pic'] = profile_pic
        user_obj['status'] = status

        temp_user_obj = user_obj

        USERSCOLL.insert(user_obj)
        del user_obj["_id"]
        self.sendJSON([temp_user_obj], "registered")



    def handleMessage(self):
        try:
            request = json.loads(self.data)
            print(request)
            if request[0] == "register":
                user_data = request[1]
                remote_jid = user_data['remoteJid']
                mobile_no = self.get_number(remote_jid)
                username = user_data['username']

                find_user = USERSCOLL.find_one({"mobile_no": mobile_no})
                if find_user == None:
                    self.register_user(user_data)
            if request[0] == "auth":
                if request[1]['type'] == "new":
                    temp_client_remoteJid = request[2]['remoteJid']
                    self.client_remoteJid = self.get_number(
                        temp_client_remoteJid)
                    self.client_file = files_dir + self.client_remoteJid + ".txt"
                    self.client_tempfile = files_dir + self.client_remoteJid + "_temp.txt"
                    print(os.path.isfile(self.client_file))
                    if os.path.isfile(self.client_file) == True:
                        os.system("mv " + self.client_file +
                                  " " + self.client_tempfile)

                        f = open(self.client_tempfile, "r")
                        messages_list = []
                        for line in f:
                            print(line[:-2])
                            messages_list.append(json.loads(line[:-2]))
                        l = messages_list
                        os.system("rm " + self.client_tempfile)

                    else:
                        l = []

                    clientInstances[self.client_remoteJid] = self
                    self.sendJSON([{"status": "success"}], "auth")
                    self.sendJSON([{"data": l}], "q")

            elif request[0] == "action" and request[1]['add'] == "relay":
                send_to = request
                send_to = send_to[2]
                print(send_to)
                send_to[0]["key"]["fromMe"] = False
                send_to[0]["messageTimestamp"] = str(int(time.time()))
                message_id = send_to[0]["key"]["id"]

                receiverJid = send_to[0]["key"]["remoteJid"]
                if "@s.whatsapp.com" in receiverJid:
                    send_to[0]["key"]["remoteJid"] = self.client_remoteJid + \
                        "@s.whatsapp.com"
                    receiver_number = self.get_number(receiverJid)

                    self.sendToReceiver(receiver_number, send_to)
                    self.sendMessageReceipt(
                        self.client_remoteJid, receiver_number, 1, message_id, "")
                elif "@g.us" in receiverJid:
                    send_to[0]["participant"] = self.client_remoteJid + \
                        "@s.whatsapp.net"
                    participants = GROUPSCOLL.find_one(
                        {"gjid": receiverJid})["participants"]
                    if self.client_remoteJid + "@c.us" in participants:
                        for p in participants:
                            if p != self.client_remoteJid + "@c.us":
                                self.sendToReceiver(p, send_to)

                        self.sendMessageReceipt(
                            self.client_remoteJid, receiverJid, 1, message_id, "")

            elif request[0] == "Msg" or request[0] == "MsgInfo" and request[1]['cmd'] == 'ack':
                send_to = request[1]
                self.sendMessageReceiptData(send_to, request[0])

            elif request[0] == "Chat" and request[1]['cmd'] == 'action' and request[1]['data'][0] == 'create':
                self.create_new_group(request)

            elif request[0] == "Chat" and request[1]['cmd'] == 'action' and request[1]['data'][0] == 'add':
                self.add_members_in_group_process(request)

            elif request[0] == "query" and request[1] == 'GroupMetadata':
                group_id = request[2]
                self.get_group_data(group_id)

            elif request[0] == "update":
                data = request[1]
                type = data['type']
                if type == 'picture':
                    jid = data['jid']
                    eurl = data['eurl']
                    tag = data['tag']

                    # user_data = 

        except:
            print(traceback.format_exc())

    def handleConnected(self):
        self.sendJSON([{"from": "backend", "type": "connected"}], "connected")
        # for client in self.server.connections.itervalues():
        #     print(client)
        print(self.address, "connected to backend")

    def handleClose(self):
        whatsapp.disconnect()
        print(self.address, "closed connection to backend")


server = SimpleWebSocketServer("", 9011, WhatsAppWeb)
print("whatsapp-web-backend listening on port 9011")
server.serveforever()



