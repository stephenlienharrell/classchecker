import logging
import os
import datetime

from pytz.gae import pytz

import jinja2
import webapp2
from google.appengine.api import mail
from google.appengine.ext import ereporter

import base_handler
import config

UTC = pytz.UTC
eastern = pytz.timezone('US/Eastern')

ereporter.register_logger()

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                   config.TEMPLATE_DIRECTORY)))


class EmailNotifyHTML(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'

    path = os.path.join(os.path.dirname(__file__),
                        config.TEMPLATE_DIRECTORY, 'email_notify.html')
    template_values = {'app_name': config.APP_NAME,
                       'year': datetime.datetime.now().year,
                       'class_number': 'INET 101',
                       'school_name': 'Internet University',
                       'term_name': 'Fall 2011',
                       'section_number': 12345,
                       'seats_available': 2,
                       'last_checked': datetime.datetime.utcnow().replace(
                                    tzinfo=UTC).astimezone(
                                    eastern).strftime(
                                    "%A, %d %B %Y %I:%M%p %Z")}

    template = jinja_environment.get_template('email_notify.html')
    page = template.render(template_values)
    self.response.out.write(page)


class EmailNotifyText(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'

    path = os.path.join(os.path.dirname(__file__),
                        config.TEMPLATE_DIRECTORY, 'email_notify.txt')
    template_values = {'app_name': config.APP_NAME,
                       'year': datetime.datetime.now().year,
                       'class_number': 'INET 101',
                       'school_name': 'INET University',
                       'section_number': 12345,
                       'term_name': 'Fall 2011',
                       'seats_available': 2,
                       'last_checked': datetime.datetime.utcnow().replace(
                                    tzinfo=UTC).astimezone(
                                    eastern).strftime(
                                    "%A, %d %B %Y %I:%M%p %Z")}

    page = open(path, ('r')).read() % template_values
    self.response.out.write(page)

class SendTestEmail(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    mail_type = self.request.get('mail_type')
    to = self.request.get('to')
    
    text_path = os.path.join(os.path.dirname(__file__), config.TEMPLATE_DIRECTORY,
                             'email_%s.txt' % mail_type)
    template = jinja_environment.get_template('email_notify.html')

    template_values = {'app_name': config.APP_NAME,
                       'year': datetime.datetime.now().year,
                       'class_number': 'INET 101',
                       'school_name': 'INET University',
                       'section_number': 12345,
                       'term_name': 'Fall 2011',
                       'seats_available': 2,
                       'last_checked': datetime.datetime.utcnow().replace(
                                    tzinfo=UTC).astimezone(
                                    eastern).strftime(
                                    '%A, %d %B %Y %I:%M%p %Z')}

    sender_address = 'ClassChecker! Automated Notifier <info@classtastic.com>'
    subject = 'Test ClassChecker %s email' % mail_type
    message = mail.EmailMessage(sender=sender_address,
                                subject=subject)
    message.to = to
    message.body = open(text_path, 'r').read() % template_values
    message.html = template.render(template_values)

    message.send()
    self.response.out.write('Mail Sent')


app = webapp2.WSGIApplication([('/email_preview/notify.html',
                                 EmailNotifyHTML),
                                ('/email_preview/notify.txt',
                                 EmailNotifyText),
                                ('/email_preview/send_test_email',
                                  SendTestEmail)],
                                 debug=True)

