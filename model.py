from google.appengine.ext import db

class JID(db.Model):
    jid = db.StringProperty(required=True)
    token = db.StringProperty(required=True)
    user = db.UserProperty()
    created = db.DateTimeProperty(required=True, auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    alias = db.StringProperty(required=False, default='')
    active = db.BooleanProperty(default=True)
    
class PostHook(db.Model):
    jid = db.ReferenceProperty(JID)
    token = db.StringProperty(required=True)
    format = db.TextProperty(required=True, default="""
query_argument:{{get_argument("subject")}}
query_argument:{{get_argument("msg")}}
""")
    created = db.DateTimeProperty(required=True, auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    active = db.BooleanProperty(default=True)

class ReceiveHook(db.Model):
    jid = db.ReferenceProperty(JID)
    token = db.StringProperty(required=True)
    endpoint = db.LinkProperty(required=True, default='http://example.com/api/receive_endpoint')
    command = db.StringProperty(required=False, default='/command')
    active = db.BooleanProperty(default=False)
    created = db.DateTimeProperty(required=True, auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
