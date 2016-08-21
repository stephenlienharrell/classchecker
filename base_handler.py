import logging
import config

import webapp2
from google.appengine.ext import ereporter

ereporter.register_logger()

class BaseRequestHandler(webapp2.RequestHandler):
  def handle_exception(self, exception, debug_mode):
    import datetime
    import os
    import sys
    import traceback
    from google.appengine import runtime
    from google.appengine.api import memcache
    from google.appengine.api import users
    from google.appengine.api import xmpp
    import jinja2
    import config

    exception_name = sys.exc_info()[0].__name__
    exception_details = str(sys.exc_info()[1])
    exception_traceback = ''.join(traceback.format_exception(*sys.exc_info()))
    logging.exception(str(exception_traceback))
    exception_expiration = 10800 # seconds (max 1 mail per three hours for a particular exception)
    user_gtalk = config.ADMIN_EMAIL
    throttle_name = 'exception-'+exception_name
    throttle = memcache.get(throttle_name)
    if throttle is None:
      try:
        if xmpp.get_presence(user_gtalk):
          memcache.add(throttle_name, 1, exception_expiration)
          msg = "ClassChecker! Error! Alert! Alert! \n\n%s: %s\n\n%s" % (
              exception_name, exception_details, exception_traceback)
          xmpp.send_message(user_gtalk, msg)
      except (runtime.DeadlineExceededError, runtime.apiproxy_errors.DeadlineExceededError):
        logging.exception("Jabber message failed")
    template_values = {'app_name': config.APP_NAME,
                       'year': datetime.datetime.now().year,}
    if users.is_current_user_admin():
       template_values['traceback'] = exception_traceback
    self.error(500)
    jinja_environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                       config.TEMPLATE_DIRECTORY)))
    template = jinja_environment.get_template('about.html')
    self.response.out.write(template.render(template_values))

