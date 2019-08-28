#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
# from utilities import *
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import traceback, json, time, os, sys, pymongo
from Crypto import Random

sys.dont_write_bytecode = True
# reload(sys)
# sys.setdefaultencoding("utf-8")
clientInstances = {}

files_dir = "/media/viral999g/G/Projects/WA_socket/client_files/"

MYCLIENT = pymongo.MongoClient("mongodb://localhost:27017/",
                            connect=False)

MYDB = MYCLIENT['wa']
GROUPSCOLL = MYDB['groups']


class WhatsAppWeb(WebSocket):
    client_remoteJid = None
    client_file = None
    client_tempfile = None
    def sendJSON(self, obj, tag):
        if "from" not in obj:
            obj["from"] = "backend"
        # print("sending " + json.dumps(obj))
        self.sendMessage("[" + tag + "," + json.dumps(obj) + "]")

    def sendError(self, reason, tag):
        print("sending error: " + reason)
        self.sendJSON({"type": "error", "reason": reason}, "error")

    def sendToReceiver(self, receiverJid, message):
        message = "{'add': 'relay'}," + json.dumps(message)
        if receiverJid in clientInstances:
            clientInstances[receiverJid].sendJSON(message, "action")

        self.appendToFile(receiverJid, message, "action")
    
    def appendToFile(self,receiverJid, message, tag):
        file = open(files_dir + receiverJid + ".txt", "a+")
        file.write("," + "[" + tag + "," + str(message) + "]")

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
                    participants = GROUPSCOLL.find_one({"remoteJid": receiverJid})["participants"]
            
                    for p in participants:
                        if p != self.client_remoteJid:
                            self.sendToReceiver(p, send_to)

                    self.sendMessageReceipt(self.client_remoteJid, receiverJid, 1, message_id, "")

            elif request[0] == "Msg" or request[0] == "MsgInfo" and request[1]['cmd'] == 'ack':
                send_to = request[1]
                self.sendMessageReceiptData(send_to, request[0])

                    
                

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
