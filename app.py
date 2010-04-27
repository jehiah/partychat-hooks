import functools
import logging
import urllib

import tornado.web
import tornado.escape
import tornado.template

from google.appengine.api import users
# from google.appengine.ext import db
from google.appengine.api import xmpp

import lib
import model

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
        # LOOKUP from whence this came
        message = xmpp.Message(self.request.body)
        logging.info('got message %s' % message.body)

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
        jid = self.get_argument('jid').lower()
        token = lib.get_new_token('jid')
        obj = model.JID(jid=jid,
            user=self.current_user,
            token=token)
        obj.put()
        self.redirect('/edit/' + token)
        
class EditHook(BaseHandler):
    @authenticated
    def get(self, token):
        if not token.startswith('H_'):
            raise tornado.web.HTTPError(404)
            
        obj = lib.get_token(token)
        if not obj:
            raise tornado.web.HTTPError(404)
        self.render('edit.html', jid=obj)

    @authenticated
    def post(self, token):
        obj = lib.get_token(token, self.current_user)
        if not obj:
            raise tornado.web.HTTPError(404)
        if self.get_argument('action.update_alias', None):
            alias = self.get_argument('alias')
            if obj.alias != alias and alias:
                obj.alias = alias
                obj.put()
                lib.send(obj, '/alias %s' % alias)
        
        if self.get_argument('action.new_post_hook', None):
            t = model.PostHook(
                token=lib.get_new_token('post'),
                jid=obj
            )
            t.put()
        if self.get_argument('action.update_post_hook', None):
            hook_token = self.get_argument('token')
            if hook_token.startswith('P_'):
                t = lib.get_token(hook_token, self.current_user)
                if t:
                    t.format = self.get_argument('format')
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
        t = tornado.template.Template(format)
        return t.generate(**args)
        
    def get(self, token):
        if not token.startswith('P_'):
            raise tornado.web.HTTPError(404)
        obj = lib.get_token(token)
        if not obj:
            raise tornado.web.HTTPError(404)

        msg = self.render_string(obj.format, post_json=None)
        lib.send(obj.jid, msg)
            
    def post(self, token):
        if not token.startswith('P_'):
            raise tornado.web.HTTPError(404)
        obj = lib.get_token(token)
        if not obj:
            raise tornado.web.HTTPError(404)

        post_json = None
        try:
            if self.request.body:
                post_json = tornado.escape.json_decode(self.request.body)
        except:
            logging.info('unable to load json from post body')
            
        msg = self.render_string(obj.format, post_json = post_json)
        lib.send(obj.jid, msg)
        
        
        