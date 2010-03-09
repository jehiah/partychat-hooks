import logging
import uuid

from google.appengine.api import xmpp
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from model import Hook

class XMPPHandler(webapp.RequestHandler):
    def post(self):
        message = xmpp.Message(self.request.POST)
        logging.info('got message %s' % message.body)
        # if message.body[0:5].lower() == 'hello':
        #     message.reply("Greetings!")
        # .reply('/snooze 1d') ?

class EditHook(webapp.RequestHandler):
    def get(self, token):
        q = Hook.all()
        q.filter('token =', token)
        hook = q.get()
        if not hook:
            self.redirect('/')
            return
        self.response.headers['Content-type'] = 'text/html'
        self.response.out.write('''
    <html><body>
    <h1>partychat - hooks</h1>
    <p>This is a hook for posting into <a href="http://partychapp.appspot.com/">http://partychapp.appspot.com/</a></p>
    <hr/>
    <p>Edit Hook</p>
    <form method="post" action="/edit/%(token)s">
    <label>jid:<input type="text" name="jid" size="40" value="%(jid)s"></label><br/>
    <label>format:<input type="text" name="format" size="80" value="%(format)s"></label><br/>
    <label>chat room alias:<input type="text" name="alias" size="20" value="%(alias)s"></label><br/>
    <button type="submit">Update Hook</button>
    </form>
    </body>
    </html>
    ''' % {
        'format' : hook.format,
        'alias' : hook.alias,
        'jid' : hook.jid,
        'token' : hook.token,
        })

    def post(self, token):
        q = Hook.all()
        q.filter('token =', token)
        hook = q.get()
        if not hook:
            self.redirect('/')
            return
        
        hook.format = self.request.get('format')
        hook.jid = self.request.get('jid')
        if hook.alias != self.request.get('alias'):
            hook.alias = self.request.get('alias')
            from_address = '%s@partychat-hooks.appspotchat.com' % token
            message = '/alias %s' % hook.alias
            try:
                output = xmpp.send_message(hook.jid, message, from_address)
                self.response.out.write('sent: %s to %s' % (message, hook.jid))
            except:
                logging.exception('failed to send message %s to %s' % (message, hook.jid))
        hook.put()
        self.response.out.write('Hook Updated')
            
        
class PostHook(webapp.RequestHandler):
    """
    this accepts a http get/post on a token and passes that message to the associated jid
    """
    def get(self, token):
        logging.info('token is %s' % token)
        
        q = Hook.all()
        q.filter('token =', token)
        hook = q.get()
        if not hook:
            self.response.out.write('token %s not configured' % token)
            return
            
        message_format = hook.format or '%(msg)s'
        
        message_params = {}
        for key in self.request.arguments():
            message_params[key] = self.request.get(key)
        
        if not message_params:
            self.response.out.write('no parameters')
            return
        
        # build an empty dictionary with all thekeys necesary for this message format
        while True:
            try:
                message = message_format % message_params
                break
            except KeyError, e:
                message_params[e.message] = ''
                continue
            self.response.out.write('unable to format message')
            return
                
            
        from_address = '%s@partychat-hooks.appspotchat.com' % token
        logging.info('sending from %s to %s message:%s' % (from_address, hook.jid, message))
        try:
            output = xmpp.send_message(hook.jid, message, from_address)
            self.response.out.write('sent: %s to %s' % (message, hook.jid))
        except:
            logging.exception('failed to send message %s to %s' % (message, hook.jid))
            self.response.out.write('error sending message')
        return
        
    def post(self, token):
        self.get(token)

class SetupHandler(webapp.RequestHandler):
    """
    this links a jid (chatroom@partychapp.appspotchat.com) with a token@partychat-hooks.appspotchat.com
    """
    def get(self):
        jid = self.request.get('jid','').lower().strip()
        if jid:
            return self.load(jid)
        
        self.response.headers['Content-type'] = 'text/html'
        self.response.out.write('''
<html><body>
<h1>partychat - hooks</h1>
<p>This is a hook for posting into <a href="http://partychapp.appspot.com/">http://partychapp.appspot.com/</a></p>
<hr/>
<p>To create a link between a http post endpoint and a jabber endpoint do the following:</p>
<form method="post" action="/">
<label>jid:<input type="text" name="jid" size="40" value="[chatroom]@partychapp.appspotchat.com"></label><br/>
<label>format:<input type="text" name="format" size="80" value="%(msg)s"></label><br/>
<button type="submit">Create Hook</button>
</form>
<hr/>

<p>If you are using cvsdude.com, a good post commit hook would be:</p>
<pre>
%%(author)s commited: %%(log)s\nhttp://%%(organization)s.trac.cvsdude.com/%%(project)s/changeset/%%(youngest)s\n\n== Files Changed == \n%%(changed)s
</pre>
</body>
</html>
''')

    def post(self):
        jid = self.request.get('jid').lower().strip()
        self.load(jid)

    def load(self, jid):
        # q = Hook.all()
        # q.filter('jid =', jid)
        # hook = q.get()
        # if not hook:
        # always create a new hook
        hook = Hook(token=unicode(uuid.uuid4()), jid=jid)
        if self.request.get('format',''):
            hook.format = self.request.get('format')
            if len(hook.format) > 512:
                return self.response.out.write('format is too long')
        hook.put()
        self.response.headers['Content-type'] = 'text/plain'
        self.response.out.write('''
        
Your HTTP Post endpoint is:

    http://partychat-hooks.appspot.com/post/%(token)s
    
Also, invite the following address into your chat room

    %(token)s@partychat-hooks.appspotchat.com
    
You can edit this hook later at:

    http://partychat-hooks.appspot.com/edit/%(token)s

''' % {'token': hook.token})
        

application = webapp.WSGIApplication([('/_ah/xmpp/message/chat/', XMPPHandler),
                                    ('/$', SetupHandler),
                                    (r'^/post/([^/]*)$', PostHook),
                                    (r'^/edit/([^/]*)$', EditHook),
                                    ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
    
    