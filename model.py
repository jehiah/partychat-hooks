from google.appengine.ext import db


class Hook(db.Model):
  jid = db.StringProperty(required=True)
  token = db.StringProperty(required=True)
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  format = db.TextProperty(required=True, default='%(msg)s')
  alias = db.StringProperty(required=False, default='')
  