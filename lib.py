
import uuid
import model
import base64
import logging
from google.appengine.api import xmpp

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
    return token

def get_token(token):
    if token.startswith('P_'):
        q = model.PostHook.all()
    elif token.startswith('H_'):
        q = model.JID.all()
    elif token.startswith('R_'):
        q = model.ReceiveHook.all()
    else:
        raise Exception('invalid token %s' % str(token))
    q.filter('token =', token)
    return q.get()
    
def get_user_jids(username):
    q = model.JID.all()
    q.filter('user =', username)
    return q.fetch(50)
    
def send(jid, msg):
    from_address = '%s@partychat-hooks.appspotchat.com' % jid.token
    try:
        output = xmpp.send_message(jid.jid, msg, from_address)
        logging.info('sent msg; output was %s' % str(output))
        return output
    except:
        logging.exception('failed to send message %s to %s' % (msg, jid.jid))
        return False
    
