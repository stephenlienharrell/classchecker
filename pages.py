import datetime
import json
import logging
import os
import re
import uuid

from google.appengine import runtime
from google.appengine.api import app_identity
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.api import xmpp

import braintree
import jinja2
from pytz.gae import pytz

import base_handler
import config
import core_lib
import db_lib
import db_models
import html_helpers
import terms
import blockchain_info


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                   config.TEMPLATE_DIRECTORY)))

def GetLoginLogoutString(auth_user):
  try:
    if auth_user:
      log_in_out = ("| %s (<a href=\"%s\">logout</a>) |" %
                    (auth_user.nickname(), users.create_logout_url("/")))
    else:
      log_in_out = ("| <a href=\"%s\">Login with your Google Account</a> |" %
                    users.create_login_url("/"))
  except (runtime.DeadlineExceededError, runtime.apiproxy_errors.DeadlineExceededError):
    logging.exception("Can't get URL from API so give empty string")
    log_in_out = ''
    
  return log_in_out


class WarmupPage(base_handler.BaseRequestHandler):
  def get(self):
    logging.info('Warmup Request') 


class NotFoundPage(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    self.error(404)
    template_values = {'app_name': config.APP_NAME,
                       'year': datetime.datetime.now().year,}

    template = jinja_environment.get_template('404.html')
    page = template.render(template_values)
    if config.REMOVE_WHITESPACE == True:
      page = re.sub(">\s*<","><", page)
    self.response.out.write(page)


class RobotsPage(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    robots_txt = ('Sitemap: http://www.classtastic.com/sitemap.xml\n'
                  'User-agent: *\n'
                  'Disallow: /images/\n')
    self.response.out.write(robots_txt)


class TermsOfUsePage(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    html = '<html><body>%s</body></html>' % terms.TERMS
    self.response.out.write(html)


class SitemapPage(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    site_map = ('<?xml version="1.0" encoding="utf-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                '  <url>\n'
                '    <loc>http://www.classtastic.com/</loc>\n'
                '    <priority>1.0</priority>\n'
                '  </url>\n'
                '  <url>\n'
                '    <loc>http://www.classtastic.com/about</loc>\n'
                '    <priority>0.9</priority>\n'
                '  </url>\n'
                '  <url>\n'
                '    <loc>http://www.classtastic.com/press/current</loc>\n'
                '    <priority>0.8</priority>\n'
                '  </url>\n'
                '  <url>\n'
                '    <loc>http://www.classtastic.com/terms</loc>\n'
                '    <priority>0.1</priority>\n'
                '  </url>\n'
                '  <url>\n'
                '    <loc>http://www.classtastic.com/flyers/ClassCheckerFlyer.pdf</loc>\n'
                '    <priority>0.5</priority>\n'
                '  </url>\n'
                '  <url>\n'
                '    <loc>http://www.classtastic.com/flyers/ClassCheckerFlyerBW.pdf</loc>\n'
                '    <priority>0.5</priority>\n'
                '  </url>\n'
                '  <url>\n'
                '    <loc>http://www.classtastic.com/flyers/ClassCheckerFlyerGray.pdf</loc>\n'
                '    <priority>0.5</priority>\n'
                '  </url>\n'
                '  <url>\n'
                '    <loc>http://www.classtastic.com/terms</loc>\n'
                '    <priority>0.1</priority>\n'
                '  </url>\n'
                '</urlset>\n')
    self.response.out.write(site_map)

class LandingPage(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    auth_user = users.get_current_user()
    school_list = db_lib.ListSchools()
    school_list.sort()
    template_values = {'app_name': config.APP_NAME,
                       'app_description': config.APP_DESCRIPTION,
                       'app_tagline': config.APP_TAGLINE,
                       'school_cslist': ','.join(school_list),
                       'school_list': '</li><li>'.join(school_list),
                       'year': datetime.datetime.now().year,
                       'contact_email': config.CONTACT_EMAIL,
                       'login_logout': GetLoginLogoutString(auth_user)}
                         
    template = jinja_environment.get_template("landing.html")
    page = template.render(template_values)
    if config.REMOVE_WHITESPACE == True:
      page = re.sub(">\s*<","><", page)
    self.response.out.write(page)

class AboutPage(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    auth_user = users.get_current_user()
    school_list = db_lib.ListSchools()
    school_list.sort()
    template_values = {'app_name': config.APP_NAME,
                       'app_description': config.APP_DESCRIPTION,
                       'app_tagline': config.APP_TAGLINE,
                       'school_list': '</li><li>'.join(school_list),
                       'year': datetime.datetime.now().year,
                       'contact_email': config.CONTACT_EMAIL,
                       'login_logout': GetLoginLogoutString(auth_user)}
                         
    template = jinja_environment.get_template('about.html')
    page = template.render(template_values)
    if config.REMOVE_WHITESPACE == True:
      page = re.sub(">\s*<","><", page)
    self.response.out.write(page)

class AccountPage(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    auth_user = users.get_current_user()
    if auth_user is None:
      logging.info('Redirecting to login page')
      self.redirect(users.create_login_url(self.request.uri))
      return
    message = ''
    class_redirect_message = self.request.get('class_redirect_message')
    if class_redirect_message == '1':
      message = ('Please update your notification information '
                 'before using the classes page.')

    school_options = html_helpers.CreateSchoolOptions()
    timezone_options = html_helpers.CreateTimezoneOptions()

    template_values = {'app_name': config.APP_NAME,
                       'year': datetime.datetime.now().year,
                       'contact_email': config.CONTACT_EMAIL,
                       'message': message,
                       'school_options': school_options,
                       'timezone_options': timezone_options,
                       'login_logout': GetLoginLogoutString(auth_user)}

    template = jinja_environment.get_template('account.html')
    page = template.render(template_values)
    if config.REMOVE_WHITESPACE == True:
      page = re.sub(">\s*<","><", page)
    self.response.out.write(page)

    

class ClassesPage(base_handler.BaseRequestHandler):
 
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    user = None
    auth_user = users.get_current_user()
    if not auth_user:
      logging.info('Redirecting to login page')
      self.redirect(users.create_login_url(self.request.uri))
      return

    user = db_lib.GetModelByKeyName('User', auth_user.user_id())
    if user is None:
      logging.info('Redirecting to account page')
      self.redirect('/account?class_redirect_message=1')
      return

    school_options = html_helpers.CreateSchoolOptions()

    template_values = {'app_name': config.APP_NAME,
                       'school_options': school_options,
                       'year': datetime.datetime.now().year,
                       'login_logout': GetLoginLogoutString(auth_user),
                       'secure_ajax_url': config.SECURE_AJAX_URL,
                       'braintree_js_encryption_key': 
                           config.BRAINTREE_JS_ENCRYPTION_KEY}

    template = jinja_environment.get_template('classes.html')
    page = template.render(template_values)
    if config.REMOVE_WHITESPACE == True:
      page = re.sub(">\s*<","><", page)
    self.response.out.write(page)

class AjaxLibPage(base_handler.BaseRequestHandler):

  def options(self):
    # check for the correct url and give it back as the origin for some cross site 
    # javascript action, again at the begining of the post
    if ('Origin' in self.request.headers and
        (self.request.headers['Origin'] == 'http://www.classtastic.com' or 
         self.request.headers['Origin'].endswith('%s.appspot.com' % 
                                                app_identity.get_application_id()))):
      self.response.headers.add_header('Access-Control-Allow-Origin', 
                                       self.request.headers['Origin'])
       
    self.response.headers.add_header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Credentials')
    return
    

  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('This page only takes a POST')

  def post(self):
    if ('Origin' in self.request.headers and
        (self.request.headers['Origin'] == 'http://www.classtastic.com' or 
        self.request.headers['Origin'].endswith('%s.appspot.com' % 
                                                app_identity.get_application_id()))):
      self.response.headers.add_header('Access-Control-Allow-Origin', 
                                       self.request.headers['Origin'])

    if not self.request.get('func'):
      logging.error('No function specified')
      return

    auth_user = users.get_current_user()

    ssl_user_auth = self.request.get('ssl_user_auth')

    if ssl_user_auth:
      auth_user = memcache.get(ssl_user_auth)
      memcache.delete(ssl_user_auth)

    if not auth_user:
      logging.warning('No authorized user, exiting')
      return

    user = db_lib.GetModelByKeyName('User', auth_user.user_id())
    user_not_needed_functions = ['GetUserInfo',
                                 'UpdateUserInfo']
    if (user is None and 
        self.request.get('func') not in user_not_needed_functions):
      return

    logging.info('Calling %s' % self.request.get('func'))
    self.response.headers['Content-Type'] = 'application/json'

    
    if self.request.get('func') == 'GetAuthForSSL':
      self.response.out.write(json.dumps(
                                  {'ssl_user_auth': db_lib.CreateSSLUserString(auth_user)}))
      return


    if self.request.get('func') == 'ListCurrentSectionsForUser':
      self.response.out.write(json.dumps(
          db_lib.GetCurrentSectionsForUser(user)))

    elif self.request.get('func') == 'AddSectionForUser':
      return_response = {'error': 0, 'message': 'Class added'}
      section_number = self.request.get('section_number')

      if not section_number:
        return_response['error'] = 1
        return_response['message'] = 'No course number given'
        self.response.out.write(json.dumps(return_response))
        return

      # EVERYBODY GETS FREE CLASSES
      paid = True

      # TESTERS GET FREE CLASSES
#      if user.primary_email.lower() in config.TESTERS:
#        paid = True

      school_name = self.request.get('school_select')
      term_number = self.request.get('term_select')

      try:
        section, _ = core_lib.FetchClassAndUpdateSection(school_name,
                                                         term_number,
                                                         section_number)

      except (urlfetch.Error, core_lib.ReturnCodeWasNot200,
              core_lib.ClassPageNotParsableError), error_message:
        return_response['error'] = 1
        return_response['message'] = ('Unable to find class %s. '
                                      'University site may be down '
                                      'or under maintainance. '
                                      'Please check the CRN and semester and '
                                      'try again.' % section_number)
        self.response.out.write(json.dumps(return_response))
        return

      user_section_key_name = '%s%s' % (section.key().name(),
                                        user.user.user_id())
      user_section = db_lib.GetModelByKeyName('UserSection',
                                              user_section_key_name) 
      if user_section is None:
        try:
          user_section = db_lib.CreateModel(
              'UserSection', {'section': section,
                              'user': user,
                              'school': section.term.school,
                              'paid': paid})
        except Exception, error_message:
          return_response['error'] = 1
          return_response['message'] = ('Unknown internal error, '
                                        'request not completed')
          self.response.out.write(json.dumps(return_response))
          logging.exception(error_message)
          return

      else:
        # user section exists so just activate it
        user_section.active = True
        user_section.deactived_reason = None
        db_lib.UpdateModel(user_section)

      db_lib.LogMetric(user_section, 'class_added_to_ui')

      memcache.delete('UserSectionListFor%s' % user.user.user_id())

      self.response.out.write(json.dumps(return_response))
     
    elif self.request.get('func') == 'DeleteSectionForUser':
      class_key = self.request.get('class_key')
      return_response = {'error': 0, 'message': 'Class deleted'}
      if not class_key:
        return_response['error'] = 1
        return_response['message'] = ('Request malformed')
        logging.warning('Delete user section request with no class_key')
        self.response.out.write(json.dumps(return_response))
        return
      
      user_section = db_lib.GetModelByKeyName('UserSection', class_key)
      if user_section is None:
        return_response['error'] = 1
        return_response['message'] = ('Request malformed')
        logging.warning('Delete user section request with bad class_key')
        self.response.out.write(json.dumps(return_response))
        return
      section_user = db_lib.GetChild(user_section, 'user')
      if section_user.user.user_id() != auth_user.user_id():
        return_response['error'] = 1
        return_response['message'] = ('Request malformed')
        logging.error('Delete user section request for section not owned '
                      'by auth user. section requested: %s, requesting user: %s'
                      % class_key, auth_user.user_id())
        self.response.out.write(json.dumps(return_response))
        return

      user_section.active = False
      user_section.deactived_reason = config.DEACTIVATE_ERRORS['USEROFF']
      user_section.pending_transaction = False
      try:
        db_lib.UpdateModel(user_section)
      except Exception, error_message:
        return_response['error'] = 1
        return_response['message'] = ('Unknown internal error, request not '
                                      'completed')
        self.response.out.write(json.dumps(return_response))
        logging.exception(error_message)
        return
 
      memcache.delete('UserSectionListFor%s' % user.user.user_id())

      db_lib.LogMetric(user_section, 'user_deactivated_class')

      self.response.out.write(json.dumps(return_response))

    elif self.request.get('func') == 'GetCurrentSchoolForUser':
      self.response.out.write(json.dumps(
          db_lib.GetCurrentSchoolForUser(user)))

    elif self.request.get('func') == 'GetTermsForSchool':
      self.response.out.write(json.dumps(
          db_lib.ListTermsForSchool(
            self.request.get('school_name').replace('_', ' '))))

    elif self.request.get('func') == 'GetUserInfo':
      if user is None:
        user_dict = {'current_user': False,
                     'email': auth_user.email(),
                     'timezone': config.DEFAULT_TIMEZONE,
                     'gtalk_id': auth_user.email(),}
      else:
        user_dict = {'current_user': True,
                     'email': user.primary_email,
                     'cell_phone': user.cell_phone,
                     'timezone': user.timezone,
                     'gtalk_id': user.gtalk_id,}
        current_school = db_lib.GetCurrentSchoolForUser(user)
        if current_school is not None:
          user_dict['school'] = current_school.replace(' ', '_'),
      self.response.out.write(json.dumps(user_dict))

    elif self.request.get('func') == 'UpdateUserInfo':
      return_response = {'error': 0, 'message': 'User updated'}
      if not mail.is_email_valid(self.request.get('primary_email')):
          return_response['error'] = 1
          return_response['message'] = ('Invalid primary email addresss, ' 
                                        'please try again')
          self.response.out.write(json.dumps(return_response))
          return
      if (self.request.get('gtalk_id') and
          not mail.is_email_valid(self.request.get('gtalk_id'))):
        return_response['error'] = 1
        return_response['message'] = ('Invalid Jabber/Google Talk ID, ' 
                                      'it should be formated like an '
                                      'email address')
        self.response.out.write(json.dumps(return_response))
        return
      try:
        if user is None:
          user_dict = {'user': auth_user,
                       'primary_email': self.request.get('primary_email'),
                       'cell_phone': self.request.get('cell_phone'),
                       'gtalk_id': self.request.get('gtalk_id'),
                       'timezone': self.request.get('timezone'),}
          to_delete = []
          for k, v in user_dict.iteritems():
            if not v:
              to_delete.append(k)
          for k in to_delete:
            del user_dict[k]
          user = db_lib.CreateModel('User', user_dict)
          user_current_school = db_lib.CreateModel(
              'UserCurrentSchool', {'user': user,
                                    'school': db_lib.GetModelByKeyName(
                                        'School',
                                         self.request.get(
                                             'school').replace('_', ' '))})
        else:
          match_list = ['primary_email', 'cell_phone', 'gtalk_id', 'timezone']
          for match in match_list:
            if self.request.get(match):
              if getattr(user, match) != self.request.get(match):
                setattr(user, match, self.request.get(match))
          db_lib.UpdateModel(user)

          user_current_school = db_lib.GetModelByKeyName(
              'UserCurrentSchool', '%sCurrentSchool' % user.user.user_id())
          logging.info(self.request.get('school'))
          if (user_current_school is None or 
              user_current_school != self.request.get('current_school')):
            user_current_school = db_lib.CreateModel(
                'UserCurrentSchool', {'user': user,
                                      'school': db_lib.GetModelByKeyName(
                                          'School',
                                           self.request.get(
                                             'school').replace('_', ' '))})
            memcache.delete('%sCurrentSchoolName' % user.user.user_id()) 
            memcache.delete('%sCurrentSchool' % user.user.user_id()) 
      except Exception, error_message:
        raise
        return_response['error'] = 1
        return_response['message'] = ('Unknown internal error, request not '
                                      'completed.')
        self.response.out.write(json.dumps(return_response))
        logging.exception(error_message)
        return
      self.response.out.write(json.dumps(return_response))
     
    elif self.request.get('func') == 'SendJabberInvitation':
      return_response = {'error': 0, 'message': 'Invitation sent to %s' % 
                                                user.gtalk_id}
      if not user.gtalk_id:
        return_response['error'] = 1
        return_response['message'] = ('No gtalk_id found, please enter one and '
                                      'save')
        self.response.out.write(json.dumps(return_response))
        return

      try:
        xmpp.send_invite(user.gtalk_id)
      except Exception, error_message:
        return_response['error'] = 1
        return_response['message'] = ('Unknown internal error, invite request '
                                      'not completed.')
        self.response.out.write(json.dumps(return_response))
        logging.exception(error_message)
        return
     
      self.response.out.write(json.dumps(return_response))
       
    elif self.request.get('func') == 'SendJabberTestMessage':
      return_response = {'error': 0, 'message': 'Test message sent to %s' % 
                                                user.gtalk_id}
      if not user.gtalk_id:
        return_response['error'] = 1
        return_response['message'] = ('No gtalk_id found, please enter one and '
                                      'save')
        self.response.out.write(json.dumps(return_response))
        return
      if not xmpp.get_presence(user.gtalk_id):
        return_response['error'] = 1
        return_response['message'] = ('User %s not currently online, please '
                                      'login your chat client and try again' % 
                                      user.gtalk_id) 
        self.response.out.write(json.dumps(return_response))
        return
      try:
        xmpp.send_message(user.gtalk_id,
                          'This is a test message from ClassChecker!')
      except Exception, error_message:
        return_response['error'] = 1
        return_response['message'] = ('Unknown internal error, invite request '
                                      'not completed.')
        self.response.out.write(json.dumps(return_response))
        logging.exception(error_message)
        return
      self.response.out.write(json.dumps(return_response))
       
    elif self.request.get('func') == 'SendSMSTestMessage':
      return_response = {'error': 0, 'message': 'Test message sent to %s' % 
                                                user.cell_phone}
      if not user.cell_phone:
        return_response['error'] = 1
        return_response['message'] = ('No cell phone found, please enter '
                                      'one and save')
        self.response.out.write(json.dumps(return_response))
        return

      message = '%s sent this test message from ClassChecker!' % (
          auth_user.email())
      try:
        core_lib.SendSMS(user.cell_phone, message)
      except Exception, error_message:
        return_response['error'] = 1
        return_response['message'] = ('Unknown internal error, invite request '
                                      'not completed.')
        self.response.out.write(json.dumps(return_response))
        logging.exception(error_message)
        return
      self.response.out.write(json.dumps(return_response))
 
    elif self.request.get('func') in ['SubmitCart', 'SubmitBitcoinCart', 'SubmitPromoCart']:
      return_response = {'error': 0, 'message': ''}
      # don't take anymore money
      return_response = {'error': 1, 'message': 'This is a free service now'}
      return return_response

      if not self.request.host_url.startswith('https'):
        return_response['error'] = 1
        return_response['message'] = ('Data not sent securely')
        self.response.out.write(json.dumps(return_response))
        return
        
      user_sections_to_post = []
      user_sections = db_lib.GetReferenceSet('UserSection', 'User', 'user',
                                             user.key().name(),
                                             {'active': True, 'paid': False,
                                              'pending_transaction': False})

      total_cost = 0
      for user_section in user_sections:
        section = db_lib.GetChild(user_section, 'section')
        if section.seats_available > 0:
          continue
        if (hasattr(section, 'waitlist_seats_total') and
            section.waitlist_seats_total > 0):
          continue
        
        price = core_lib.GetPaymentPrice(user_section)
        total_cost += price
        user_sections_to_post.append(user_section)

      if not user_sections_to_post:
        return_response['error'] = 1
        return_response['message'] = ('No valid sections to purchase')
        self.response.out.write(json.dumps(return_response))
        return

      order_user = user
      order_email = order_user.primary_email
      transaction_dict = {}

      if self.request.get('func') == 'SubmitCart':
        braintree.Configuration.configure(
            config.BRAINTREE_ENVIRONMENT,
            merchant_id=config.BRAINTREE_MERCHANT_ID,
            public_key=config.BRAINTREE_PUBLIC_KEY,
            private_key=config.BRAINTREE_PRIVATE_KEY
        )
        sections_list = []
        transaction_id = str(uuid.uuid4())

        for user_section in user_sections_to_post:
          sections_list.append(str(user_section.section.section_number))

        school = user_section.school.school_name
        result = braintree.Transaction.sale({
            'amount': str(total_cost),
            'credit_card': {
                'number': self.request.get('number'),
                'cvv': self.request.get('cvv'),
                'expiration_month': self.request.get('month'),
                'expiration_year': self.request.get('year')
                },
            'custom_fields': {
                'email': order_email,
                'section_list': ','.join(sections_list),
                'school': school,
                'trans_id': transaction_id,
            },
            'options': {
                'submit_for_settlement': True
                }
            })

        if not result.is_success:
          return_response['error'] = 1
          if result.transaction:
            return_response['message'] = ('Could not proccess payment: %s' % 
                                          result.transaction.processor_response_text)
          else:
            return_response['message'] = ('Could not proccess payment: %s' % 
                                          result.message)

          self.response.out.write(json.dumps(return_response))
          return

        return_response['message'] = 'Credit card processed successfully'

        order_number = 'Braintree_%s' % transaction_id
        pending_tx = False
        paid = True

        #create transaction
        transaction = db_lib.CreateModel('Transaction', {
          'order_number': order_number,
          'transaction_email': order_email,
          'user': order_user,
          'total_charge_amount': float(total_cost),
          'created_date': datetime.datetime.utcnow(),
          'charge_date': datetime.datetime.utcnow(),
        })

        for user_section in user_sections_to_post:
          # This assumes they are only purchasing at one school
          db_lib.LogMetric(user_section, 'credit_card_charged')

        sender_address = 'ClassChecker! Automated Notifier <info@classtastic.com>' 
        subject = 'Notifications active on ClassChecker!'
        template_values = {'school': school,
                           'sections_list_string': ','.join(sections_list)}
        text_path = os.path.join(os.path.dirname(__file__),
                                 config.TEMPLATE_DIRECTORY,
                                 'email_braintree_notify.txt')
        message = mail.EmailMessage(sender=sender_address, subject=subject)
        message.to = user.primary_email
        text_portion = open(text_path, 'r').read() % template_values
        message.body = text_portion
        template = jinja_environment.get_template('email_braintree_notify.html')
        message.html = template.render(template_values)
        try:
          message.send()
          logging.info('Sent mail:\n%s' % text_portion)
        except Exception:
          logging.exception('Mail: %s to %s failed' % (text_portion, user.primary_email))



      elif self.request.get('func') == 'SubmitBitcoinCart':
        #request.host_url is the base for the callback url. don't hardcode something
        #because it changes for testing and production server
        btc_address = blockchain_info.GetBitcoinAddress()
        btc_amount = len(user_sections_to_post) * config.DEFAULT_SECTION_COST_BTC
        
        return_response['address'] = btc_address
        return_response['amount'] = btc_amount

        pending_tx = True
        paid = False
        transaction = None

        user_section_list = map(lambda user_section: str(user_section.key().name()), user_sections_to_post)

        db_lib.CreateModel('PendingTransaction', {
           'order_number': btc_address,
           'total_satoshi_amount': blockchain_info.toSatoshi(btc_amount),
           'total_dollar_amount': float(total_cost),
           'transaction_email': order_email,
           'user': user,
           'user_section_list': user_section_list,
        })

        for user_section in user_sections_to_post:
          db_lib.LogMetric(user_section, 'waiting_for_bitcoin_payment')


      elif self.request.get('func') == 'SubmitPromoCart':
        codes = db_lib.GetReferenceSet('PromoCode', 'User', 'user', user.user.user_id(),
                                      {'active': True})
        num_free_classes = reduce(lambda code_count, code: code_count+code.uses_left, codes, 0)

        if num_free_classes < len(user_sections_to_post):
          return_response['error'] = 1
          return_response['message'] = 'Not enough promo codes for all unpaid classes. Please remove some classes.'
          self.response.out.write(json.dumps(return_response))
          return

        #This shit makes me want to vomit but whatever. Fuck it.
        #oh and this shit worked first try. 1337 status acheived.
        i = 0
        j = 0 #steps along user_sections_to_post async to any loop
        for code in codes:
          for i in range(code.uses_left):
            if j < len(user_sections_to_post):
              transaction = db_lib.CreateModel('Transaction', {
                'order_number': code.code,
                'transaction_email': order_email,
                'user': order_user,
                'total_charge_amount': float(core_lib.GetPaymentPrice(user_sections_to_post[j])),
                'created_date': datetime.datetime.utcnow(),
                'charge_date': datetime.datetime.utcnow(),
              })

              user_sections_to_post[j].pending_transaction = None
              user_sections_to_post[j].paid = True
              user_sections_to_post[j].transaction = transaction
              db_lib.UpdateModel(user_sections_to_post[j])

              j += 1
              code.uses_left -= 1

              if code.uses_left == 0:
                code.active = False
              db_lib.UpdateModel(code)
      #endif

      if self.request.get('func') != 'SubmitPromoCart':
        #we do this differently for submitpromo.
        #so only do this crap if we are using CC/BTC
        for user_section in user_sections_to_post:
          user_section.pending_transaction = pending_tx
          user_section.paid = paid
          user_section.transaction = transaction
          db_lib.UpdateModel(user_section)

      memcache.delete('UserSectionListFor%s' % user.user.user_id())
      return_response['error'] = 0
      #return_response['redirect_url'] = redirect_url

      self.response.out.write(json.dumps(return_response))

    elif self.request.get('func') == 'AssignPromoCode':
      return_response = {}

      code = self.request.get('promo_code')
      if not code:
        return_response['error'] = 1
        return_response['message'] = 'No code supplied'
        self.response.out.write(json.dumps(return_response))
        return

      promo_code = db_lib.GetModelByKeyName('PromoCode', 
                                            'PromoCode%s' % code)
      if promo_code is None:
        return_response['error'] = 1
        return_response['message'] = 'Promo code %s not found' % code
        self.response.out.write(json.dumps(return_response))
        return

      code_user = db_lib.GetChild(promo_code, 'user')
      if code_user != None:
        return_response['error'] = 1
        return_response['message'] = 'Promo code already redeemed'
        self.response.out.write(json.dumps(return_response))
        return

      promo_code.user = user
      db_lib.UpdateModel(promo_code)
      return_response['error'] = 0
      return_response['message'] = 'Promo code loaded successfully'
        
      self.response.out.write(json.dumps(return_response))
      
    elif self.request.get('func') == 'GetCurrentPromoAmount':
      self.response.out.write(db_lib.GetFreeClassesForUser(auth_user.user_id()))
      return 

    #### EVERYTHING AFTER THIS IS ADMIN ONLY

    elif not users.is_current_user_admin():
      return

    elif self.request.get('func') == 'CreatePromoCode':
      return_response = {}
      reason = self.request.get('promo_reason')
      user_id = self.request.get('promo_user')
      uses = self.request.get('promo_uses')
      
      if reason is None:
        return_response['error'] = 1
        return_response['message'] = 'Reason not posted'
      elif not uses.isdigit() or int(uses) < 1:
        return_response['error'] = 1 
        return_response['message'] = ('uses must be a number and must be '
                                      'greater than 0')
      elif user_id == 'None' and uses != '1':
        return_response['error'] = 1 
        return_response['message'] = ('user_id was not set but there are more '
                                     'than one uses')
      else:
        if user_id == 'None':
          user = None
        else:
          user = db_lib.GetModelByKeyName('User', user_id)
        uses = int(uses)
        if uses > 1:
          use_type = 'multi'
        else:
          use_type = 'single'

        promo_code = core_lib.CreatePromoCode(use_type, reason, uses, user)
        return_response['error'] = 0
        return_response['message'] = 'Promo Code created successfully: %s' % (
            promo_code)

      self.response.out.write(json.dumps(return_response))

    elif self.request.get('func') == 'DeactivatePromoCode':
      return_response = {}
      promo_code_text = self.request.get('promo_code')
      promo_code = db_lib.GetModelByKeyName('PromoCode',
                                            'PromoCode%s' % promo_code_text)
      promo_code.active = False

      db_lib.UpdateModel(promo_code)
      return_response['error'] = 0
      return_response['message'] = 'Promo code deactivated'
      self.response.out.write(json.dumps(return_response))

    elif self.request.get('func') == 'ListPromoCodes':
      query = db_models.PromoCodeModel.all()

      promo_code_list = []
      for promo_code in query:
        promo_code_dict = db_lib.db.to_dict(promo_code)
        promo_code_dict['date'] = str(promo_code_dict['date']) #a datetime.datetime will not JSON serialize
        promo_code_list.append(promo_code_dict)
      for promo_code_dict in promo_code_list:
        if promo_code_dict['user'] is None:
          promo_code_dict['user'] = ''
        else:
          promo_code_dict['user'] = db_lib.GetModelByKeyName(
              'User', promo_code_dict['user'].name()).primary_email
      self.response.out.write(json.dumps(promo_code_list))
        
    elif self.request.get('func') == 'GetAllUsers':
      user_list = []
      query = db_models.UserModel.all()
      for user in query:
        user_list.append(db_lib.db.to_dict(user))
      for user in user_list:
        user['user'] = user['user'].user_id()

      sorted_user_list = sorted(user_list, key=lambda k: k['primary_email']) 
      self.response.out.write(json.dumps(sorted_user_list))

    else:
      logging.error('Function %s not found' % self.request.get('func'))
