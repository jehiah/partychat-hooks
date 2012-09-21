import functools
import logging

import tornado.web
import tornado.template
from tornado.escape import json_decode
from tornado.escape import utf8 as _utf8

from google.appengine.api import users
# from google.appengine.ext import db
# from google.appengine.api import xmpp
from google.appengine.api import urlfetch

import lib
import model
import urllib

def authenticated(method):
    """Decorate methods with this to require that the user be logged in."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method == "GET":
                url = self.get_login_url()
                if "?" not in url:
                    url += "?" + urllib.urlencode(dict(next=self.request.uri))
                self.redirect(url)
                return
            raise tornado.web.HTTPError(403)
        return method(self, *args, **kwargs)
    return wrapper

class XMPPHandler(tornado.web.RequestHandler):
    def post(self):
        # stanza = self.get_argument('stanza')
        from_addr = self.get_argument('from')
        to_addr = self.get_argument('to').lower()
        body = self.get_argument('body')
        logging.info('got message %s from %s to %s' % (body, from_addr, to_addr))
        # message = xmpp.Message({'from' : from_addr, 'to' : to_addr, 'body' : body})
        
        token = to_addr.split('@',1)[0]
        try:
            jid = lib.lookup_token(token)
        except:
            logging.info('no jid found for %s' % token)
            return self.finish('RECEIVE HOOK NOT FOUND')
        
        if not jid:
            logging.info('jid requested, but not found for %s' % token)
            return self.finish('RECEIVE HOOK NOT FOUND')
        
        for receive_hook in jid.receivehook_set:
            if receive_hook.endpoint == 'http://example.com/api/receive_endpoint':
                # skip default
                continue
            if not receive_hook.active:
                continue
            if lib.match_command(receive_hook.command, body):
                data = urllib.urlencode({'from':from_addr, 'body': _utf8(body), 'partychat-hook':jid.token, 'on-behalf-of':_utf8(jid.user.nickname())})
                try:
                    urlfetch.fetch(
                        receive_hook.endpoint,
                        method='POST',
                        payload=data,
                        headers = {'Content-Type' : 'application/x-www-form-urlencoded'},
                        follow_redirects=False
                        )
                    logging.info('send to %s' % receive_hook.endpoint)
                except:
                    logging.exception('failed writing to %s for %s with data %s' % (receive_hook.endpoint, receive_hook.token, data))
            else:
                logging.info('no command match for %s against %s' % (repr(receive_hook.command), repr(body)))
        self.finish('DONE')

class BaseHandler(tornado.web.RequestHandler):
    """Implements Google Accounts authentication methods."""
    def get_current_user(self):
        user = users.get_current_user()
        if user: user.administrator = users.is_current_user_admin()
        return user
    
    def get_login_url(self):
        return users.create_login_url(self.request.uri)
    
    def get_logout_url(self):
        return users.create_logout_url(self.request.uri)
    
    def render_string(self, template_name, **kwargs):
        # Let the templates access the users module to generate login URLs
        return tornado.web.RequestHandler.render_string(
            self, template_name, users=users, **kwargs)

class MainHandler(BaseHandler):
    def get(self):
        if self.current_user:
            user_jids = lib.get_user_jids(self.current_user)
            self.render('my_jids.html', user_jids = user_jids)
        else:
            self.render('home.html')

class AddJID(BaseHandler):
    @authenticated
    def get(self):
        self.render('add.html')
    
    @authenticated
    def post(self):
        jid = self.get_argument('jid')
        token = lib.get_new_token('jid')
        obj = model.JID(jid=jid,
            user=self.current_user,
            token=token)
        obj.put()
        self.redirect('/edit/' + token)

class EditHook(BaseHandler):
    @authenticated
    def get(self, token):
        if not token.startswith('h_'):
            raise tornado.web.HTTPError(404)
        
        obj = lib.lookup_token(token)
        if not obj:
            raise tornado.web.HTTPError(404)
        if obj.user != self.current_user:
            raise tornado.web.HTTPError(404)
        self.render('edit.html', jid=obj)
    
    @authenticated
    def post(self, token):
        obj = lib.lookup_token(token, self.current_user)
        if not obj:
            raise tornado.web.HTTPError(404)
        if self.get_argument('action.update_alias', None):
            alias = self.get_argument('alias')
            if obj.alias != alias and alias:
                obj.alias = alias
                obj.put()
                lib.send(obj, '/alias %s' % alias)

        elif self.get_argument('action.partychat_migration', None):
            obj.jid = obj.jid.replace('im.partych.at', 'at.partych.at')
            obj.put()
        
        elif self.get_argument('action.new_post_hook', None):
            t = model.PostHook(
                token=lib.get_new_token('post'),
                jid=obj
            )
            t.put()
        elif self.get_argument('action.update_post_hook', None):
            hook_token = self.get_argument('token')
            if hook_token.lower().startswith('p_'):
                t = lib.lookup_token(hook_token, self.current_user)
                if t:
                    t.format = self.get_argument('format')
                    t.put()
        elif self.get_argument('action.new_receive_hook', None):
            t = model.ReceiveHook(
                token=lib.get_new_token('receive'),
                jid=obj)
            t.put()
        elif self.get_argument('action.update_receive_hook', None):
            hook_token = self.get_argument('token')
            if hook_token.lower().startswith('r_'):
                t = lib.lookup_token(hook_token, self.current_user)
                if t:
                    t.endpoint = self.get_argument('endpoint')
                    t.command = self.get_argument('command') or '*'
                    t.put()
        elif self.get_argument('action.activate', None):
            hook_token = self.get_argument('action.activate')
            t = lib.lookup_token(hook_token, self.current_user)
            if t:
                t.active = True
                t.put()
        elif self.get_argument('action.deactivate', None):
            hook_token = self.get_argument('action.deactivate')
            t = lib.lookup_token(hook_token, self.current_user)
            if t:
                t.active = False
                t.put()
        self.redirect('/edit/' + obj.token)

class PostHook(BaseHandler):
    def render_string(self, format, **kwargs):
        args = dict(
            request=self.request,
            get_argument=self.get_argument,
        )
        args.update(self.ui)
        args.update(kwargs)
        t = tornado.template.Template(format, autoescape=None)
        return t.generate(**args)
    
    def get(self, token):
        if not token.lower().startswith('p_'):
            raise tornado.web.HTTPError(404)
        obj = lib.lookup_token(token)
        if not obj or not obj.active:
            raise tornado.web.HTTPError(404)
        
        msg = self.render_string(obj.format, post_json=None)
        lib.send(obj.jid, msg)
    
    def post(self, token):
        if not token.lower().startswith('p_'):
            raise tornado.web.HTTPError(404)
        obj = lib.lookup_token(token)
        if not obj or not obj.active:
            raise tornado.web.HTTPError(404)
        
        msg = self.render_string(obj.format, json_decode=json_decode)
        lib.send(obj.jid, msg)
        
        