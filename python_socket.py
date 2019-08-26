#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
# from utilities import *
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import traceback, json, time, os, sys

sys.dont_write_bytecode = True
# reload(sys)
# sys.setdefaultencoding("utf-8")
files_dir = "/home/bharat/Downloads/WA_Socket/client_files/"

def eprint(*args, **kwargs):			# from https://stackoverflow.com/a/14981125
    print(*args, file=sys.stderr, **kwargs)


class WhatsAppWeb(WebSocket):
    clientInstances = {}
    client_remoteJid = None
    def sendJSON(self, obj, tag):
        if "from" not in obj:
            obj["from"] = "backend"
        eprint("sending " + json.dumps(obj))
        self.sendMessage(tag + "," + json.dumps(obj))

    def sendError(self, reason, tag):
        eprint("sending error: " + reason)
        self.sendJSON({"type": "error", "reason": reason}, "error")

    def handleMessage(self):
        try:
            request = json.loads(self.data)
            if request[0] == "auth":
                if request[1]['type'] == "new":
                    self.client_remoteJid = request[2]['remoteJid']
                    eprint("Auth sucess")
                    self.sendJSON({"status": "success"}, "auth")
            elif request[0] == "action" and request[1]['add'] == "relay":
                send_to = request
                send_to[2][0]["key"]["fromMe"] = True
                # with open(files_dir+send_to+".txt", 'a+') as fd:
                    # fd.write(","+str(request)+"\n")
                self.sendJSON({"message": send_to}, "auth")

        except:
            eprint(traceback.format_exc())

    def handleConnected(self):
        self.sendJSON({"from": "backend", "type": "connected"}, "connected")
        eprint(self.address, "connected to backend")

    def handleClose(self):
        whatsapp.disconnect()
        eprint(self.address, "closed connection to backend")


server = SimpleWebSocketServer("", 9011, WhatsAppWeb)
eprint("whatsapp-web-backend listening on port 9011")
server.serveforever()
