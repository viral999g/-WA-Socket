import websocket
import json
import time
import binascii
from Crypto import Random
try:
    import thread
except ImportError:
    import _thread as thread

def authProcess(ws, user_mobile):
    remoteJid = user_mobile + "@s.whatsapp.com"
    request_body = ["auth", {"type": "new"}, {"remoteJid":remoteJid}]
    ws.send(json.dumps(request_body))

def on_message(ws, message):
    print("message", message)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print("### closed ###")




def sendTextMessage(ws, to_user, message):
    messageId = "3EB0"+str(binascii.hexlify(Random.get_random_bytes(8)).upper().decode("utf-8"))
    request_body = ["action", {"add": "relay"}, [{"message": {"conversation": message}, "key": {
        "remoteJid": to_user, "id": messageId}, "messageTimestamp": str(int(time.time()))}]]
    ws.send(json.dumps(request_body))

def on_open(ws):
    def run(*args):
        authProcess(ws, "919428284313")
        sendTextMessage(ws, "917069852821@s.whatsapp.com", "test msg 2")
        print("thread terminating...")
    thread.start_new_thread(run, ())


def on_auth(ws):
    print(auto)


if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("ws://localhost:9011/",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    # ws.on_auth = on_auth
    ws.on_open = on_open
    ws.run_forever()
