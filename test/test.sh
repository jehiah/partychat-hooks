#!/bin/sh

# curl -H 'Content-Type: multipart/form-data; boundary="----=_Part_837529_22096737.1272429593698"' --data-binary @test_post_body.txt http://127.0.0.1:8083/_ah/xmpp/message/chat/
echo "";
curl -H 'Content-Type: multipart/form-data; boundary="----=_Part_837529_22096737.1272429593698"' --data-binary @test_receive_body.txt http://127.0.0.1:8083/_ah/xmpp/message/chat/
echo "";
