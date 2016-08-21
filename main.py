import logging

from google.appengine.ext import ereporter
import webapp2

from blockchain_info import BlockchainListener
from pages import *


ereporter.register_logger()

app = webapp2.WSGIApplication([('/', LandingPage),
                               ('/_ah/warmup', WarmupPage),
                               ('/robots.txt', RobotsPage),
                               ('/terms', TermsOfUsePage),
                               ('/sitemap.xml', SitemapPage),
                               ('/about', AboutPage),
                               ('/account', AccountPage),
                               ('/classes', ClassesPage),
                               ('/ajaxlib', AjaxLibPage),
                               ('/blockchain_notify', BlockchainListener),
                               ('/.*', NotFoundPage)],
                               debug=True)
