<h1>Web Server Socket</h1>

<h3>Connecting to Socket server</h3>
    > Host : ws://<IP_ADDR>:9011/

<h3>Logging and authentication</h3>
    > Send : ["auth", {"type": "new"}, {"remoteJid":remoteJid}]
    > Receive :
        1) [auth,{"from": "backend", "status": "success"}]
        2) [q,{"data": "[[],[action,{'add': 'relay'},[{\"key\": {\"fromMe\": false, \"id\": \"3EB09E5B1E31CE48730C\", \"remoteJid\": \"917069852821@s.whatsapp.com\"}, \"message\": {\"conversation\": \"Test msg\"}, \"messageTimestamp\": \"1566970464\"}]]]", "from": "backend"}]
        
        in (2), data contains array of socket messages in queue.
        
<h3>Send message to user (1-2-1)</h3>
    > Send : ["action", {"add": "relay"}, [{"message": {"conversation": 'message'}, "key": {
    "remoteJid": '919428284313@s.whatsapp.com', "fromMe": True, "id": '3EB0A1ED1B05362823BC'}, "messageTimestamp":'1566970629'}]]
    > Receive : [Msg,{'id': '3EB0A1ED1B05362823BC', 'ack': 1, 'cmd': 'ack', 'to': '919428284313@c.us', 't': 1566970629, 'from': '917069852821@c.us'}]
        
    remoteJid -> Jid of user to whom the message is to be sent
    id -> Message Id of the message (Should be unique for each message)
    from -> Jid of the message sender    
    to -> Jid of the message receiver
    
<h3>Message received by user (1-2-1)</h3>
    > Receive : [action,{'add': 'relay'},[{"key": {"fromMe": false, "id": "3EB0A1ED1B05362823BC", "remoteJid": "917069852821@s.whatsapp.com"}, "message": {"conversation": "Test msg"}, "messageTimestamp": "1566970629"}]]
    > Send : [Msg,{'id': '3EB0A1ED1B05362823BC', 'ack': 2, 'cmd': 'ack', 'to': '919428284313@c.us', 't': '1566971275', 'from': '917069852821@c.us'}]
        
    remoteJid -> Jid of user to whom the message is to be sent
    id -> Message Id of the message (Should be unique for each message)
    from -> Jid of the message sender    
    to -> Jid of the message receiver
    ack -> Status/type of acknowledgement like delievered, read.

<h3>Send message to Group</h3>
    > Send : [action,{'add': 'relay'},[{"key": {"fromMe": true, "id": "3EB09ACC2D709AB09850", "remoteJid": "917069852821-1566557065@g.us"}, "message": {"conversation": "Test msg Group"}, "messageTimestamp": "1566971560"}]]
    > Receive : [Msg,{'id': '3EB09ACC2D709AB09850', 'ack': 1, 'cmd': 'ack', 'to': '917069852821-1566557065@g.us', 't': 1566971560, 'from': '917069852821'}]
     
    Web socket will send the message to all the participants of the group using the group Jid (remoteJid)
    
<h3>Message received in Group</h3>
    > Receive : [action,{'add': 'relay'},[{"key": {"fromMe": false, "id": "3EB09ACC2D709AB09850", "remoteJid": "917069852821-1566557065@g.us"}, "participant": "917069852821@s.whatsapp.net", "message": {"conversation": "Test msg Group"}, "messageTimestamp": "1566971560"}]]
    > Send : [MsgInfo, {"from": "917069852821@c.us", "ack": 2, "cmd": "ack","to": "917069852821-1566557065@g.us", "participant": "919428284313@sc.us" , "id": "3EB0F517CDA590E6B488", "t": "1566971560"}]
