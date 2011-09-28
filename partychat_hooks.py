import os
import tornado.web
import tornado.wsgi
import wsgiref.handlers

# application imports
import app

class Application(tornado.wsgi.WSGIApplication):
    def __init__(self):
        app_settings = { 
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "debug" : True,
            "autoescape" : None,
        }
        handlers = [
            (r"^/$", app.MainHandler),
            (r'/_ah/xmpp/message/chat/', app.XMPPHandler),
            (r'^/add$', app.AddJID),
            (r'^/edit/(h_[^/]*)$', app.EditHook),
            (r'^/post/([pP]_[^/]*)$', app.PostHook),
        ]
        tornado.wsgi.WSGIApplication.__init__(self, handlers, **app_settings)
        
if __name__ == "__main__":
    application = Application()
    wsgiref.handlers.CGIHandler().run(application)