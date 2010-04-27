import tornado.web
import tornado.wsgi
import wsgiref.handlers
import os

import app


class Application(tornado.wsgi.WSGIApplication):
    def __init__(self):
        app_settings = { 
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "debug" : True
        }
        handlers = [
            (r"/", app.MainHandler),
            (r'/_ah/xmpp/message/chat/', app.XMPPHandler),
            (r'^/add$', app.AddJID),
            (r'^/edit/([^/]*)$', app.EditHook),
            (r'^/post/([^/]*)$', app.PostHook),
        ]
        tornado.wsgi.WSGIApplication.__init__(self, handlers, **app_settings)
        
if __name__ == "__main__":
    application = Application()
    wsgiref.handlers.CGIHandler().run(application)