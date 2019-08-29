import sys
sys.dont_write_bytecode = True

import os, pymongo
import signal
import base64
from threading import Thread, Timer
import math
import time
import datetime
import json
import io
from time import sleep
from threading import Thread
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import hashlib
import hmac
import traceback

import websocket
import curve25519
import pyqrcode
from utilities import *
from whatsapp_binary_reader import whatsappReadBinary
from whatsapp_binary_writer import whatsappWriteBinary
import binascii
from Crypto import Random

from whatsapp_defines import WATags, WASingleByteTokens, WADoubleByteTokens, WAWebMessageInfo, WAMetrics


myclient = pymongo.MongoClient("mongodb://localhost:27017/",
                            connect=False)

MYDB = myclient['wa']
VILLAGESCOLL = MYDB['commands']




def HmacSha256(key, sign):
    return hmac.new(key, sign, hashlib.sha256).digest()

def HKDF(key, length, appInfo=""):						# implements RFC 5869, some parts from https://github.com/MirkoDziadzka/pyhkdf
    key = HmacSha256("\0"*32, key)
    keyStream = ""
    keyBlock = ""
    blockIndex = 1
    while len(keyStream) < length:
        keyBlock = hmac.new(key, msg=keyBlock+appInfo+chr(blockIndex), digestmod=hashlib.sha256).digest()
        blockIndex += 1
        keyStream += keyBlock
    return keyStream[:length]

def AESPad(s):
    bs = AES.block_size
    return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)

def to_bytes(n, length, endianess='big'):
    h = '%x' % n
    s = ('0'*(len(h) % 2) + h).zfill(length*2).decode('hex')
    return s if endianess == 'big' else s[::-1]

def AESUnpad(s):
    return s[:-ord(s[len(s)-1:])]

def AESEncrypt(key, plaintext):							# like "AESPad"/"AESUnpad" from https://stackoverflow.com/a/21928790
    plaintext = AESPad(plaintext)
    iv = os.urandom(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(plaintext)

def WhatsAppEncrypt(encKey, macKey, plaintext):
    enc = AESEncrypt(encKey, plaintext)
    return HmacSha256(macKey, enc) + enc				# this may need padding to 64 byte boundary

def AESDecrypt(key, ciphertext):						# from https://stackoverflow.com/a/20868265
    iv = ciphertext[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext[AES.block_size:])
    return AESUnpad(plaintext)



websocketIsOpened = False
onOpenCallback = None
onMessageCallback = None
onCloseCallback = None
activeWs = None
messageSentCount = 0
websocketThread = None
messageQueue = {}																# maps message tags (provided by WhatsApp) to more information (description and callback)
loginInfo = {
    "clientId": 'j0yvufNmzIwjrbCWqCPUwQ==',
    "serverRef": '1@BzOvyLs1BKcSOPHlbGVRL9bQZBHc/JsCvjCmZOxDRlIh9LT+Prhpn/vN',
    "privateKey": None,
    "publicKey": None,
    "key": {
        "encKey": "\xe5\xf5\xed\xd6\xd8s\xb9\xba]=\xd1\xbe\x8d\xbb&H\xbd\xe9+\xb0\x9b&\x18\x02'\xd5\xdc\x13\x1b\xbaL\xe8",
        "macKey": '\xa4=&\x97YD\x19(\xd0\xbc\xe1\xe3\xc1\x1b\xa2\xe4\xbc\xe5\x17J\x18\x16\xe7qe\xe8w\x94T\x16\xa4\xe0'
    }
}
connInfo = {
    "clientToken": 'PDTKLommUhpUu0kF84V4HIAWxLPRQ+meHdcS9+9XuDQ=',
    "serverToken": '1@+NFbRhgJ8juQX7aaUGI6YPF1pT31PfSdJZ4Q7492fHHnRTJvKwSv5SUTab9Uyn1e6XiF1Mu+Qj7+pA==',
    "browserToken": '1@s0kuQC4JBjSAt1OzVZQD+3aG2ruSq/jbRChZdlZQC1JZr+X90XXnqaPJZN0Kvl+tt66bLjQMaBgTPSOGd8AiWHVStBeMFys3FB36XXt5LGzm/vPlLKk7X6ISkmvcmOOtkJROBXWbSIYqfyNA/lQVVg==',
    "secret": '+sql6jZo8M1tNPQqppHEsWfK7aRNlFgk8DwNOYNioQ0Gwh2MOF+xd3c7eDPRTAWQsQ1uRggXPACDnujqzb7cGiedgWIDRNODa4avCFB1MdHwOrWK6vulLRsnYgimnTKZ7lWbJmNYfIOyvxtaR5Ok7uheRtREV2JzZP/tExV5uSaBQLaZrPT0ZpSuYD94T/8t',
    "sharedSecret": None,
    "me": None
}

# loginInfo["privateKey"] = curve25519.Private()
# loginInfo["publicKey"] = loginInfo["privateKey"].get_public()

# connInfo["sharedSecret"] = loginInfo["privateKey"].get_shared_key(curve25519.Public(connInfo["secret"][:32]), lambda a: a)
# sse = connInfo["sharedSecretExpanded"] = HKDF(connInfo["sharedSecret"], 80)

# keysEncrypted = sse[64:] + connInfo["secret"][64:]
# keysDecrypted = AESDecrypt(sse[:32], keysEncrypted)
# loginInfo["key"]["encKey"] = keysDecrypted[:32]
# loginInfo["key"]["macKey"] = keysDecrypted[32:64]

messageContent = '33454230444245333844413432353333383035432c108063408df51de46da50ba5a8249ab8180890be3cfb75404f0d3012e1457b3beaad23ee831240ebc5d913f134eec51dea6ada4755350800f1ee1954a40bb8eb1a7b5c6eadade080e22ab2fbf553baa142811481e66f603d706f55f787921ce73860ffbd753c1bf4ae9ec769565556b2c22a8497d0046fdd2cf02ba110d0c3f3207c8c61b085ae1f04b1e7b1b0d6e86b0745'

print(loginInfo["key"])

if messageContent != "":
  hmacValidation = HmacSha256(loginInfo["key"]["macKey"], messageContent[32:])
  # if hmacValidation != messageContent[:32]:
  #     raise ValueError("Hmac mismatch")
  
  decryptedMessage = AESDecrypt(loginInfo["key"]["encKey"], messageContent[32:])
  # try:
  processedData = whatsappReadBinary(decryptedMessage, True)
  messageType = "binary"
  print(processedData)

  # except:
  processedData = { "traceback": traceback.format_exc().splitlines() }
  messageType = "error"
  # finally:
  #   print("Error")

