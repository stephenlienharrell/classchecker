
import logging

from google.appengine.ext import ereporter
import webapp2
from press_pages import *


ereporter.register_logger()

app = webapp2.WSGIApplication([('/press/rss.xml', PressRssFeed),
                               ('/press/.*', PressPage)],
                                   debug=True)

