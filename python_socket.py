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

files_dir = "/home/bharat/Downloads/WA_Socket/client_files/"

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
        print("sending " + json.dumps(obj))
        self.sendMessage(tag + "," + json.dumps(obj))

    def sendError(self, reason, tag):
        print("sending error: " + reason)
        self.sendJSON({"type": "error", "reason": reason}, "error")

    def sendToReceiver(self, receiverJid, message):
        if receiverJid in clientInstances:
            clientInstances[receiverJid].sendJSON(json.dumps(message), "auth")

        file = open(files_dir + receiverJid + ".txt", "a+")
        file.write("," + str(message) + "\n")

    def handleMessage(self):
        try:
            request = json.loads(self.data)
            if request[0] == "auth":
                if request[1]['type'] == "new":
                    temp_client_remoteJid = request[2]['remoteJid']
                    at_the_rate_index = temp_client_remoteJid.find("@")
                    self.client_remoteJid = temp_client_remoteJid[0:at_the_rate_index]
                    self.client_file = files_dir + self.client_remoteJid + ".txt"
                    self.client_tempfile = files_dir + self.client_remoteJid + "_temp.txt"
                    print(os.path.isfile(self.client_file))
                    if os.path.isfile(self.client_file) == True:
                        os.system("mv " + self.client_file + " " + self.client_tempfile)

                        f = open(self.client_tempfile, "r")
                        l = "[[]" + str(f.read()).replace("\n", "") + "]"
                        print(l)
                    else:
                        l = ""

                    clientInstances[self.client_remoteJid] = self
                    self.sendJSON({"status": "success"}, "auth")
                    self.sendJSON({"data": l}, "q")
                    os.system("rm " + self.client_tempfile)
            elif request[0] == "action" and request[1]['add'] == "relay":
                send_to = request
                send_to[2][0]["key"]["fromMe"] = False
                send_to[2][0]["messageTimestamp"] = str(int(time.time()))
                message_id = send_to[2][0]["key"]["id"]

                receiverJid = send_to[2][0]["key"]["remoteJid"]
                if "@s.whatsapp.com" in receiverJid:
                    send_to[2][0]["key"]["remoteJid"] = self.client_remoteJid + "@s.whatsapp.com"
                    self.sendToReceiver(receiverJid, send_to)
                    self.sendMessageReceipt(self.client_remoteJid, receiverJid, 1, message_id)
                elif "@g.us" in receiverJid:
                    send_to[2][0]["participant"] = self.client_remoteJid + "@s.whatsapp.net"
                    participants = GROUPSCOLL.find_one({"remoteJid": receiverJid})["participants"]
            
                    for p in participants:
                        if p != self.client_remoteJid:
                            self.sendToReceiver(p, send_to)

                    self.sendMessageReceipt(self.client_remoteJid, receiverJid, 1, message_id)
                    
                

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
