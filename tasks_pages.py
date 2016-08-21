import datetime
import json
import logging
import math
import os
import sys
import threading
import time
import uuid


import jinja2
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.api import xmpp
from google.appengine.ext import ereporter

from pytz.gae import pytz
from xml.dom import minidom

import base_handler
import config
import core_lib
import db_lib
import db_models

ereporter.register_logger()

UTC = pytz.utc

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                   config.TEMPLATE_DIRECTORY)))

class UpdateSchools(base_handler.BaseRequestHandler):
  class UpdateSchoolThread(threading.Thread):
  
    def __init__(self, school_name, base_url):
      self.base_url = base_url
      self.school_name = school_name
      self.school_updated = False
      threading.Thread.__init__(self)

    def run(self):
      start_time = time.time()
      base_url = self.base_url
      full_url = '%s%s' % (base_url, config.TERM_PAGE)
      rpc = urlfetch.create_rpc(deadline=10)
      headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.66 Safari/535.11'}
      urlfetch.make_fetch_call(rpc, full_url, headers=headers)
    
      log_messages = [] 
      school_name = self.school_name
      log_messages.append('Checking School: %s' % school_name)

      school = db_lib.GetModelByKeyName('School', school_name)
      if school is None:
        log_messages.append('==Adding School')
        school = db_lib.CreateModel('School', {'school_name': school_name,
                                               'base_url': base_url})
        school_updated = True
      else:
        school_dict = {}
        school_dict['school_name'] = school_name
        school_dict['base_url'] = base_url
        school_dict['active'] = True
        school_dict['deactived_reason'] = None
        school_updated = db_lib.CompareAndUpdateModel(school, school_dict)
        if school_updated:
          log_messages.append('--Updating School')

      school_term_keys = db_lib.GetSetKeys(school, 'school', 'Term', {'active': True})

      try:   
        result = rpc.get_result()
      except urlfetch.Error as e:
        logging.exception('Unable to fetch ' + full_url)
        raise type(e), type(e)(e.message + '\nUnable to fetch ' + full_url), sys.exc_info()[2]

      if not result.status_code == 200:
        try:
          raise core_lib.ReturnCodeWasNot200('Page fetch: %s\n  status was not 200: %s' % (
              full_url, result.status_code))

        except core_lib.ReturnCodeWasNot200, error_message:
          if result.status_code == 404:
            logging.exception('File not found')
          else:
            logging.error(error_message)
        return
      try:
        term_updated = False
        for term_name, term_number in core_lib.GetCurrentTerms(result).iteritems():
          term_number = int(term_number)
          term = db_lib.GetModelByKeyName('Term', '%s%s' % (school.school_name,
                                                          term_number))
          if term is None:
            log_messages.append('==Adding term: %s' % term_name)
            term = db_lib.CreateModel('Term', {'term_name': term_name,
                                               'term_number': int(term_number),
                                               'school': school})
            term_updated = True
          else:
            term_dict = {}
            term_dict['term_name'] = term_name
            term_dict['term_number'] = int(term_number)
            term_dict['school'] = school
            term_dict['active'] = True
            term_dict['deactived_reason'] = None
            term_updated = db_lib.CompareAndUpdateModel(term, term_dict)
            if term_updated:
              log_messages.append('--Updating term: %s' % term_name)

          term_key = term.key().name()
          if term_key in school_term_keys:
            school_term_keys.remove(term_key)
      except Exception:
        logging.exception('school_name: %s, term_name: %s' % (school_name, term_name))
        return

      try:
        for key in school_term_keys:
          delete_key = db_models.TermModel.get_by_key_name(key)
          db_lib.DeactivateActivityModel(delete_key,
                                         config.DEACTIVATE_ERRORS['NOTERM'])
      except Exception:
        logging.exception('school_name: %s, key_to_delete: %s' % (school_name, key))
        return

      if term_updated:
        memcache.delete('%sTerms' % school.school_name)
      if term_updated or school_updated:
        self.school_updated = True
      log_messages.append('Run time: %s' % (time.time() - start_time))
      logging.info('\n'.join(log_messages))

  ### check the schools first and just update the changes
  def get(self):
    output_lines = []
    update_school_threads = []
    for school_name, school_info in config.SUPPORTED_SCHOOLS.iteritems():
      
      output_lines.append('Update school: %s' % school_name)
      thread = self.UpdateSchoolThread(school_name, school_info['base_url'])
      thread.start()
      update_school_threads.append(thread)
  

    query = db_models.SchoolModel.all()
    query.filter('active =', True)
  
    for school in query:
      if school.school_name not in config.SUPPORTED_SCHOOLS:
        output_lines.append('Deactivate school: %s' % school.school_name)
        db_lib.DeactivateActivityModel(school,
                                       config.DEACTIVATE_ERRORS['NOSCHOOL'])
    

    school_updated = False
    finished = False
    while(not finished):
      finished = True
      for thread in update_school_threads:
        if thread.is_alive():
          finished = False
        else:
          if not school_updated:
            school_updated = thread.school_updated
          thread.join()

    if school_updated:
      memcache.delete('school_info')

    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('School Updating Complete')


class CheckClassBySchools(base_handler.BaseRequestHandler):

  def get(self):
    output_lines = []
    schools_with_sections = []
    school_keys = config.SUPPORTED_SCHOOLS.keys()
    list_of_tasks_for_queue = []
    list_of_tasks_for_queue.append([])
    
    largest_class_count = 0
    school_info = {}
    query = db_models.UserSectionModel.all(keys_only=True)
    query.filter('active =', True)
    query.filter('paid =', True)
   
    user_sections = db_lib.MemcacheReferenceSet(query)
    keys_to_fetch = {}
    for user_section in user_sections:
      school_key = user_section.get_key_from_reference('school').name()
      if school_key not in school_info:
          school_info[school_key] = []
      section_key = user_section.get_key_from_reference('section')
      keys_to_fetch[section_key.name()] = section_key
      school_info[school_key].append(section_key.name())
      

    model_cache = db_lib.GetModelsFromDictOfKeys(keys_to_fetch)
    keys_to_fetch = {}
    for model in model_cache.values():
      term_key = model.get_key_from_reference('term')
      keys_to_fetch[term_key.name()] = term_key
    model_cache.update(db_lib.GetModelsFromDictOfKeys(keys_to_fetch))
    
    school_tasks = {}
    for school_name, section_keys in school_info.iteritems():
      for section_key in section_keys:
        section = model_cache[section_key]
        term = model_cache[section.get_key_from_reference('term').name()]
        if school_name not in school_tasks:
          school_tasks[school_name] = {}

        params_dict = {'school_name': school_name,
                       'term_number': term.term_number,
                       'term_name': term.term_name,
                       'section_number': section.section_number}
        task_name = '%s-%s-%s' % (params_dict['school_name'],
                                  params_dict['term_name'],
                                  params_dict['section_number'])
        task_name = task_name.replace(' ', '-')
        school_tasks[school_name][task_name] = params_dict
      task_count = len(school_tasks[school_name])
      if task_count > largest_class_count:
        largest_class_count = task_count
    
    del school_info
    del model_cache

    if not school_tasks:
      return

    if (((config.CLASS_CHECK_INTERVAL - config.PADDING_BEFORE_RECHECK) / 
          largest_class_count) <
          config.MINIMUM_TIME_BETWEEN_CHECKS):
      bucket_count = ((config.CLASS_CHECK_INTERVAL - config.PADDING_BEFORE_RECHECK)/
                       config.MINIMUM_TIME_BETWEEN_CHECKS)
    else:
      bucket_count = largest_class_count

    task_buckets = [[] for x in range(bucket_count)]
    class_count = 0
    for school_name, task_dict in school_tasks.iteritems():
      task_count = len(task_dict)
      if task_count < bucket_count:
        bucket_jump = math.floor(float(bucket_count) / task_count)
      else:
        bucket_jump = 1

      task_bucket_count = 0
      for task_name, params_dict in task_dict.iteritems():
        class_count += 1
        task_buckets[int(task_bucket_count)].append((task_name, params_dict))
        task_bucket_count += bucket_jump
        if task_bucket_count >= bucket_count:
          task_bucket_count = 0
        
    del school_tasks

    class_splay = ((config.CLASS_CHECK_INTERVAL -
                    config.PADDING_BEFORE_RECHECK) / bucket_count)

    list_of_tasks_for_queue = []
    list_of_tasks_for_queue.append([])
    for count, bucket in enumerate(task_buckets):
      current_queue = count/config.QUEUE_ADD_LIMIT
      if len(list_of_tasks_for_queue) < current_queue + 1:
        list_of_tasks_for_queue.append([])
      countdown = count*class_splay
      task_names = []
      params = []
      for task_info in bucket:
        task_names.append(task_info[0])
        params.append(task_info[1])

      task = taskqueue.Task(url='/tasks/check_class', countdown=countdown,
                            name='CheckClassMulti-%s' % uuid.uuid4(),
                            params={'classes': json.dumps(params)})
      list_of_tasks_for_queue[current_queue].append(task)
      self.response.headers['Content-Type'] = 'text/plain'
      info_message = ('Created MultiTask for these classes:\n\t%s' %
                      '\n\t'.join(task_names))
      self.response.out.write(info_message + '\n')
      logging.info(info_message)

    logging.info('%s classes queued for checking' % class_count)
    queue = taskqueue.Queue('class-check')
    for task_list in list_of_tasks_for_queue:
      if task_list:
        queue.add(task_list)

class CheckClass(base_handler.BaseRequestHandler):
  class CheckClassThread(threading.Thread):
    def __init__(self, school_name, term_name, term_number, section_number):
      self.term_name = term_name
      self.term_number = term_number
      self.section_number = section_number
      self.school_name = school_name
      threading.Thread.__init__(self)


    def run(self):
      term_number = self.term_number
      term_name = self.term_name
      section_number = self.section_number
      school_name = self.school_name
      try:
        section, previous_remaining = (
            core_lib.FetchClassAndUpdateSection(school_name,
                                                term_number,
                                                section_number,
                                                term_name=term_name))
      except (urlfetch.Error, core_lib.ReturnCodeWasNot200):
        return

      if( section.seats_available > 0 and 
          previous_remaining < section.seats_available ):
        user_section_dict = {}
        user_sections = db_lib.GetReferenceSet('UserSection', 'Section',
                                               'section', section.key().name(),
                                               {'active': True, 'paid': True})
        for user_section in user_sections:
          user_section_dict[user_section.created] = user_section

        user_section_keys = user_section_dict.keys()
        user_section_keys.sort()             
        tasks_to_submit = []
        for count, user_section_index in enumerate(user_section_keys):
          user_section = user_section_dict[user_section_index]
          time_since_last_notified = (config.CLASS_CHECK_INTERVAL * 
                                     (config.EMAIL_NOTIFY_SLOTS + 1))
          if user_section.last_notified is not None:
            time_since_last_notified = (
                datetime.datetime.utcnow() -
                user_section.last_notified).seconds
          if time_since_last_notified < (
            config.CLASS_CHECK_INTERVAL * config.EMAIL_NOTIFY_SLOTS):
            continue

          if count > config.EMAIL_NOTIFY_SLOTS:
            count = config.EMAIL_NOTIFY_SLOTS
          name = '%s-%s-%s-%s' % (school_name, term_name, section_number,
                                  user_section.user.user.user_id())
          name = name.replace(' ', '-')

          countdown = count * config.CLASS_CHECK_INTERVAL
          user_section.last_notified = (datetime.datetime.utcnow() +
                                        datetime.timedelta(seconds=countdown))
          logging.info('Created Task: %s' % name)
          tasks_to_submit.append(taskqueue.Task(
              url='/tasks/email_class_info', countdown=countdown+30,
              name='%s-%s' % (name, uuid.uuid4()), 
              params={'user_section_key': user_section.key().name(),
                      'school_name': school_name,
                      'term_name': term_name,
                      'section_number': section_number}))
          db_lib.UpdateModel(user_section)
        if tasks_to_submit:
           queue = taskqueue.Queue('class-check')
           queue.add(tasks_to_submit)


  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('This task only takes a POST')

  def post(self):
    class_list_json = self.request.get('classes')
    try:
      class_list = json.loads(class_list_json)
    except ValueError:
      logging.warning('Cannot load json: \n%s' % class_list_json)
      raise
    class_check_threads = []
    for class_info in class_list:
      thread = self.CheckClassThread(class_info['school_name'],
                                     class_info['term_name'],
                                     class_info['term_number'],
                                     class_info['section_number'])
      thread.start()
      class_check_threads.append(thread)

    finished = False
    while(not finished):
      finished = True
      for thread in class_check_threads:
        if thread.is_alive():
          finished = False
        else:
          thread.join()


class EmailClassInfo(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('This task only takes a POST')

  def post(self):
    user_section = db_lib.GetModelByKeyName(
        'UserSection', self.request.get('user_section_key'))
    section = db_lib.GetChild(user_section, 'section')
    if section.seats_available  < 1:
      logging.info('No e-mail sent. No available seats found for section.')
      return
    user = user_section.user
    if user.timezone is not None:
      user_timezone = pytz.timezone(user.timezone)
    else:
      user_timezone = pytz.timezone(config.DEFAULT_TIMEZONE)

    sender_address = 'ClassChecker! Automated Notifier <info@classtastic.com>'
    subject = 'A seat became available in %s' % section.class_number
    short_body = ('Message from ClassChecker!: \nA seat has opened up in %s(%s)'
                  ' at %s in %s.' % (section.class_number,
                                     self.request.get('section_number'),
                                     self.request.get('school_name'),
                                     self.request.get('term_name')))
    template_values = {'app_name': config.APP_NAME,
                       'year': datetime.datetime.now().year,
                       'class_number': section.class_number,
                       'school_name': self.request.get('school_name'),
                       'section_number': self.request.get('section_number'),
                       'term_name': self.request.get('term_name'),
                       'seats_available': section.seats_available,
                       'last_checked': section.last_checked.replace(
                                           tzinfo=UTC).astimezone(
                                           user_timezone).strftime(
                                           '%A, %d %B %Y %I:%M%p %Z')}

    template = jinja_environment.get_template('email_notify.html')
    text_path = os.path.join(os.path.dirname(__file__),
                             config.TEMPLATE_DIRECTORY,
                             'email_notify.txt')
    message = mail.EmailMessage(sender=sender_address,
                                subject=subject)
    message.to = user.primary_email
    text_portion = open(text_path, 'r').read() % template_values
    message.body = text_portion
    message.html = template.render(template_values)
    try:
      try:
        message.send()
        logging.info('Sent mail:\n%s' % text_portion)
      except Exception:
        logging.exception('Mail: %s to %s failed' % (text_portion, user.primary_email))
      if user.gtalk_id:
        try:
          xmpp.send_message(user.gtalk_id, short_body)
          logging.info('Sent Jabber message:\n%s' % short_body)
        except Exception:
          logging.exception('Jabber message: %s to %s failed' % (short_body, user.gtalk_id))
      if user.cell_phone:
        try:
          core_lib.SendSMS(user.cell_phone, short_body)
          logging.info('Sent SMS:\n%s' % short_body)
        except Exception:
          logging.exception('SMS message: %s to %s failed' % (short_body, user.cell_phone))
    finally:
      user_section.last_notified = datetime.datetime.utcnow()
      db_lib.UpdateModel(user_section)
      db_lib.LogMetric(user_section, 'seat_available_notify')
    

class DeactivationCheckerSchoolAndTerm(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    query = db_models.SchoolModel.all()
    query.filter('active =', False)
    for school in query:
      reason = school.deactived_reason
      db_lib.DeactivateActivityModel(school, reason)

    query = db_models.TermModel.all()
    query.filter('active =', False)
    for term in query:
      reason = term.deactived_reason
      db_lib.DeactivateActivityModel(term, reason)

    self.response.out.write('Deactivation Complete')


class ClearAllUserSectionListCaches(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    query = db_models.UserModel.all()
    memcache_ids = []
    for user in query:
      memcache_ids.append('UserSectionListFor%s' % user.user.user_id())
    memcache.delete_multi(memcache_ids)
    self.response.out.write('All UserSectionListForUser caches deleted')


class ShowMemcacheStats(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    stats = memcache.get_stats()
    output_lines = []
    output_lines.append('Cache hits: %s' % stats['hits'])
    output_lines.append('Cache misses: %s' % stats['misses'])
    output_lines.append('Bytes Transfered from hits: %sk' % (stats['byte_hits']/1024))
    output_lines.append('Items in cache: %s' % stats['items'])
    output_lines.append('Size of items in cache: %sk' % (stats['bytes']/1024))
    output_lines.append('Oldest item last accessed: %sm' % (stats['oldest_item_age']/60))
    self.response.out.write('\n'.join(output_lines))


class PromoCodePage(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    template_values = {}
    template = jinja_environment.get_template('promo_codes.html')
    page = template.render(template_values)
    self.response.out.write(page)

