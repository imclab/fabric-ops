#!/usr/bin/env python
#
# :copyright: (c) 2012 by Mike Taylor
# :license: BSD 2-Clause
#

import os, sys
import json
import uuid
import email
import logging

import requests
import sleekxmpp


logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

#
# read and parse the mail message delivered via STDIN
# 
# build a json string to send to PostageApp as a HTTP POST
#
# when you specify via /etc/aliases a mail_to_command
# you will receive all of the headers, a blank line and
# then the message payload
#
# using the email.FeedParser module allows us to also
# handle any incoming mail that is sent as a multipart
# mime
#
# python 2.7+
#
# depends on the requests module
#     pip install requests
#     http://docs.python-requests.org/
#

msgParser = email.FeedParser.FeedParser()

for line in sys.stdin.readlines():
    msgParser.feed(line)

msg = msgParser.close()

if msg.is_multipart():
    payload = msg.as_string()
else:
    payload = msg.get_payload()

body = { "api_key":   "HRo8SuktnubH4XErey2l0zUEMQXGrYCH",
         "uid":       str(uuid.uuid4()),
         "arguments": { "recipients": ["ops@andyet.net"],
                        "headers":    { "subject": msg.get('Subject'),
                                        "from":    "ops@andyet.net", #msg.get('From'),
                                      },
                        "content":    { "text/plain": payload }
                      }
       }

s = json.dumps(body)
r = requests.post('https://api.postageapp.com/v.1.0/send_message.json', data=s, headers={'Content-Type': 'application/json'})

h = open('/tmp/bear.out', 'w')
h.write(s)
h.write('%d %s\n' % (r.status_code, r.text))
h.close()

class AlertBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password, to, msg):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.to_list = to
        self.message = msg

        self.add_event_handler("session_start", self.start)

    def start(self, event):
        self.send_presence()
        self.get_roster()

        for jid in self.to_list:
            self.send_message(mto=jid, mbody=self.message, mtype='chat')

        self.disconnect(wait=True)

xmpp = AlertBot('alerts@code-bear.com', 'dMozCG0BC8zH', ['bear@bear.im', 'bear42@gmail.com'], payload)
xmpp.register_plugin('xep_0030') # Service Discovery
xmpp.register_plugin('xep_0199') # XMPP Ping

if xmpp.connect(('80.68.90.68', 5222)):
    xmpp.process(block=True)
