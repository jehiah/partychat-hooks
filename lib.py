
import uuid
import model
import base64
import logging
import re
from google.appengine.api import xmpp

def match_command(command, body):
    if command == '*' or \
        body.startswith(command) or \
        re.findall('^\[[^\]]+\]\s%s' % re.escape(command), body):
        return True
    return False

def get_new_token(token_type):
    if token_type is 'post':
        prefix = 'P_'
    elif token_type is 'jid':
        prefix = 'H_'
    elif token_type is 'receive':
        prefix = 'R_'
    else:
        raise Exception('invalid token type %s' % str(token_type))
    token = prefix + base64.b64encode(str(uuid.uuid4()))[:8]
    return token.lower()

def lookup_token(token, user=None):
    if token.lower().startswith('p_'):
        q = model.PostHook.all()
    elif token.lower().startswith('h_'):
        q = model.JID.all()
    elif token.lower().startswith('r_'):
        q = model.ReceiveHook.all()
    else:
        raise Exception('invalid token %s' % str(token))
    q.filter('token =', token)
    obj = q.get()
    if obj and user:
        # match that this user has ownership
        if token.startswith('h_') and obj.user != user:
            return
        elif not token.startswith('h_') and obj.jid.user != user:
            return
    return obj

def get_user_jids(username):
    q = model.JID.all()
    q.filter('user =', username)
    return q.fetch(50)

def send(jid, msg):
    from_address = '%s@partychat-hooks.appspotchat.com' % jid.token.lower()
    try:
        output = xmpp.send_message(jid.jid, msg, from_address)
        logging.info('sent msg; output was %s' % str(output))
        return output
    except:
        logging.exception('failed to send message %s to %s' % (msg, jid.jid))
        return False
    
