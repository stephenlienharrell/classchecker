import datetime
import json
import logging
import random
import uuid

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from pytz.gae import pytz

import config
import db_models

UTC = pytz.utc

class Error(Exception):
  pass

RANDOM_SAMPLE = """abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"""

def CreateSSLUserString(user):
    system_random = random.SystemRandom()
    one_time_user_key = ''.join(system_random.sample(
       RANDOM_SAMPLE, 64))
    memcache.set(one_time_user_key, value=user)
    return one_time_user_key
  

def ListTermsForSchool(school_name, memcache_reload=False):
  if not memcache_reload:
    if config.USE_MEMCACHE:
      term_info = memcache.get('%sTerms' % school_name)
      if term_info is not None:
        return term_info
  term_info = []
  terms = GetReferenceSet('Term', 'School', 'school', school_name,
                          {'active': True})
  for term in terms:
    term_info.append({'term_name': term.term_name,
                      'term_number': term.term_number})
  
  if config.USE_MEMCACHE:
    memcache.set('%sTerms' % school_name, time=86400, value=term_info)
  return term_info
    

def ListSchools(memcache_reload=False):
  schools = config.SUPPORTED_SCHOOLS.keys()
  schools.sort()
  return schools

def GetCurrentSchoolForUser(user, memcache_reload=False):
  if not memcache_reload:
    if config.USE_MEMCACHE:
      user_school = memcache.get('%sCurrentSchoolName' % user.user.user_id())
      if user_school is not None:
        return user_school

  user_current_school = GetModelByKeyName(
        'UserCurrentSchool', '%sCurrentSchool' % user.user.user_id())
  if user_current_school is None:
    return None
  school = GetChild(user_current_school, 'school')
  current_school = school.school_name
  
  if config.USE_MEMCACHE:
    memcache.set('%sCurrentSchoolName' % user.user.user_id(), time=86400,
                 value=current_school)
  return current_school

def GetSectionPlace(user_section_key, section_key):
  section_rank = 1
  user_section_dict = {}
  user_sections = GetReferenceSet('UserSection', 'Section', 'section',
                                  section_key, {'active': True})
  for user_section in user_sections:
    user_section_dict[user_section.created] = user_section.key().name()
  user_section_keys = user_section_dict.keys()
  user_section_keys.sort()
  for count, user_section_date in enumerate(user_section_keys):
    if user_section_key == user_section_dict[user_section_date]:
      section_rank = count + 1
      break

  memcache.set('%sListPlace' % user_section_key, section_rank)
  return section_rank


def GetCurrentSectionsForUser(user, memcache_reload=False):
  if user.timezone is None:
    user_timezone = config.DEFAULT
  else:
    user_timezone = user.timezone

  class_check_tasks = []
  class_check_stale_multiplyer = 4
  if not memcache_reload:
    if config.USE_MEMCACHE:
      user_sections_info = memcache.get('UserSectionListFor%s' %
                                        user.user.user_id())
      if user_sections_info is not None:
        for user_section_info in user_sections_info:

          section_key = '%s%s%s' % (
              user_section_info['school_name'],
              user_section_info['term_number'],
              user_section_info['section_number'])
          section = GetModelByKeyName('Section', section_key)
       
          if user_section_info['seats_available'] != section.seats_available:
            return GetCurrentSectionsForUser(user, memcache_reload=True)

          if ((datetime.datetime.utcnow() - section.last_checked).seconds >
              (class_check_stale_multiplyer * config.CLASS_CHECK_INTERVAL)):
            params_dict = {'school_name': user_section_info['school_name'],
                           'term_number': user_section_info['term_number'],
                           'term_name': user_section_info['term_name'],
                           'section_number': user_section_info['section_number']}
            task_name = '%s-%s-%s' % (params_dict['school_name'],
                                      params_dict['term_name'],
                                      params_dict['section_number'])

            task = taskqueue.Task(url='/tasks/check_class',
                                  name='%s-%s' % (task_name.replace(' ', '-'),
                                                  uuid.uuid4()),
                                  params={'classes': json.dumps([params_dict])})
            logging.info('Added task %s' % task_name)
            class_check_tasks.append(task)


          user_section_info['last_checked'] = section.last_checked.replace(
              tzinfo=UTC).astimezone(
              pytz.timezone(user_timezone)).strftime(
                  '%a, %d %b %Y %H:%M:%S %Z'),

          user_section_key = '%s%s%s%s' % (
              user_section_info['school_name'],
              user_section_info['term_number'],
              user_section_info['section_number'],
              user.user.user_id())
          section_rank = memcache.get('%sListPlace' % user_section_key)

          if section_rank is None:
            section_rank = GetSectionPlace(user_section_key, section_key)
          user_section_info['section_rank'] = section_rank

        if class_check_tasks:
          queue = taskqueue.Queue('class-check')
          queue.add(class_check_tasks)
        return user_sections_info

  section_list = []
  user_sections = GetReferenceSet('UserSection', 'User', 'user',
                                  user.key().name(), {'active': True})
  for user_section in user_sections:
    user_section_key = user_section.key().name()

    section = GetChild(user_section, 'section')
    section_rank = GetSectionPlace(user_section.key().name(),
                                   section.key().name())

    term = GetChild(section, 'term')
    school = GetChild(user_section, 'school')

    section_url = '%s%s' % (
        config.SUPPORTED_SCHOOLS[school.school_name]['base_url'],
        config.CLASS_PAGE % {'term_number': term.term_number,
                             'section_number': section.section_number})

    if ((datetime.datetime.utcnow() - section.last_checked).seconds >
        (class_check_stale_multiplyer * config.CLASS_CHECK_INTERVAL)):
      params_dict = {'school_name': school.school_name,
                     'term_number': term.term_number,
                     'term_name': term.term_name,
                     'section_number': section.section_number}
      task_name = '%s-%s-%s' % (params_dict['school_name'],
                                params_dict['term_name'],
                                params_dict['section_number'])

      task = taskqueue.Task(url='/tasks/check_class',
                            name='%s-%s' % (task_name.replace(' ', '-'),
                                            uuid.uuid4()),
                            params={'classes': json.dumps([params_dict])})
      logging.info('Added task %s' % task_name)
      class_check_tasks.append(task)

    if user_section.paid:
      paid = 'Paid'
      purchasable = 'No: Already purchased'
    elif user_section.pending_transaction:
      paid = 'Pending Payment Confirmation'
      purchasable = 'No: Payment pending'
    else:
      paid = 'Not Paid'
      purchasable = 'Yes'

    if section.seats_available > 0:
      purchasable = 'No: Seats are available'

    if (hasattr(section, 'waitlist_seats_total') and 
        section.waitlist_seats_total > 0):
      purchasable = 'No: There is an active waitlist at the institution'
      
    section_list.append({'paid': paid,
                         'school_name': school.school_name,
                         'term_number': term.term_number,
                         'term_name': term.term_name,
                         'section_number': section.section_number,
                         'section_name': section.class_title,
                         'key_name': user_section.key().name(),
                         'section_rank': section_rank,
                         'last_checked': section.last_checked.replace(
                             tzinfo=UTC).astimezone(
                             pytz.timezone(user_timezone)).strftime(
                             '%a, %d %b %Y %H:%M:%S %Z'),
                         'seats_available': section.seats_available,
                         'section_url': section_url,
                         'purchasable': purchasable})

  if config.USE_MEMCACHE:
    memcache.set('UserSectionListFor%s' % user.user.user_id(),
                 section_list)
  if class_check_tasks:
    queue = taskqueue.Queue('class-check')
    queue.add(class_check_tasks)
  return section_list

def GetFreeClassesForUser(user_id):
  codes = GetReferenceSet('PromoCode', 'User', 'user', user_id,
                          {'active': True})
  sum = 0
  for code in codes:
    sum += code.uses_left
  return sum

def GetModelByKeyName(model_name, key_name):
  model = None
  if config.USE_MEMCACHE:
    model = memcache.get(key_name)
  if model is None:
    model = getattr(db_models, '%sModel' % model_name).get_by_key_name(key_name)
    if config.USE_MEMCACHE:
      memcache.set(key_name, value=model)
  return model


def GetChild(parent_model, child_name):
  key = parent_model.get_key_from_reference(child_name)
  if key is None:
    return None
  key_name = key.name()
  if config.USE_MEMCACHE:
    model = memcache.get(key_name)
  if model is None:
    model = getattr(parent_model, child_name)
    if config.USE_MEMCACHE:
      memcache.set(key_name, value=model)
  return model


def GetChildAsyncSend(parent_model, child_name):
  key = parent_model.get_key_from_reference(child_name)
  key_name = key.name()
  if config.USE_MEMCACHE:
    model = memcache.get(key_name)
  if model is None:
    get_future = db.get_async(key)
    return_tuple = (False, get_future)
  else:
    return_tuple = (True, model)
  return return_tuple

def GetChildAsyncReturn(async_tuple):
  if async_tuple[0]:
    return async_tuple[1]
  else:
    model = async_tuple[1].get_result()
    if config.USE_MEMCACHE:
      memcache.set(model.key().name(), value=model)
    return model

def UpdateModel(model, async=False):
  if config.USE_MEMCACHE:
    memcache.set(model.key().name(), model)
  if async:
    return db.put_async(model)
  model.put()

def CompareAndUpdateModel(model, properties_dict):
  same = True
  for property_name, property in model.properties().items():
    if property_name not in properties_dict:
      continue
    if isinstance(property, db.ReferenceProperty):
      reference_property = GetChild(model, property_name)
      if properties_dict[property_name].key() != reference_property.key():
        same = False
      continue
    if properties_dict[property_name] != getattr(model, property_name):
      same = False

  if not same:
    for property in properties_dict.keys():
      setattr(model, property, properties_dict[property])
    UpdateModel(model)
    return True
  return False

def GetSetKeys(parent_model, parent_arg_on_child, set_type, filter_dict):
  query = getattr(db_models, '%sModel' % set_type).all(keys_only=True)
  query.filter('%s ='  % parent_arg_on_child, parent_model)
  for k, v in filter_dict.iteritems():
    query.filter('%s =' % k, v)
  return [key.name() for key in query] 

def _GetReferenceQuery(name, parent_name, parent_arg, parent_key, filter_dict):
  query = db.Query(getattr(db_models, '%sModel' % name), keys_only=True)
  query.filter('%s =' % parent_arg,
      db.Key.from_path('%sModel' % parent_name, parent_key))
  for k, v in filter_dict.iteritems():
    query.filter('%s =' % k, v) 
  return query

def MemcacheReferenceSet(query):
  return_list = []
  key_names = {}
  for key in query:
    key_names[key.name()] = key
  return GetModelsFromDictOfKeys(key_names).values()

def GetModelsFromDictOfKeys(key_names):
  entities_to_fetch = []
  entities = memcache.get_multi(key_names.keys())
  if not key_names:
    return {}
  for key_name in key_names.keys():
    if key_name not in entities:
      entities_to_fetch.append(key_names[key_name])

  db_entities = []
  if entities_to_fetch: 
    db_entities = db.get(entities_to_fetch)
  
  entities_to_memcache = {}
  for entity in db_entities:
    key_name = entity.key().name()
    entities_to_memcache[key_name] = entity
  if entities_to_memcache:
    memcache.set_multi(entities_to_memcache)
    entities.update(entities_to_memcache)
  return entities

def IsReference(name, parent_name, parent_arg, parent_key, filter_dict):
  query = _GetReferenceQuery(name, parent_name, parent_arg, parent_key, filter_dict)
  return query.count(1)

def GetReferenceQuery(name, parent_name, parent_arg, parent_key, filter_dict):
  query = _GetReferenceQuery(name, parent_name, parent_arg, parent_key, filter_dict)
  query.run()
  return query

def GetReferenceSet(name, parent_name, parent_arg, parent_key, filter_dict):
  query = GetReferenceQuery(name, parent_name, parent_arg, parent_key, filter_dict)
  return MemcacheReferenceSet(query)


def CreateModel(name, args_dict, async=False):
  if name == 'School':
    key_name = args_dict['school_name']
  elif name == 'Term':
    key_name = '%s%s' % (args_dict['school'].school_name,
                         args_dict['term_number'])
  elif name == 'User':
    key_name = args_dict['user'].user_id()
  elif name == 'UserCurrentSchool':
    key_name = '%sCurrentSchool' % args_dict['user'].user.user_id()
  elif name == 'Section':
    key_name = '%s%s%s' % (args_dict['term'].school.school_name,
                           args_dict['term'].term_number,
                           args_dict['section_number'])
  elif name == 'UserSection':
    key_name = '%s%s%s%s' % (args_dict['section'].term.school.school_name,
                             args_dict['section'].term.term_number,
                             args_dict['section'].section_number,
                             args_dict['user'].user.user_id())
  elif name == 'Transaction':
    key_name = args_dict['order_number']
  elif name == 'PendingTransaction':
    key_name = 'Pending%s' % args_dict['order_number']
  elif name == 'PromoCode':
    key_name = 'PromoCode%s' % args_dict['code']
  else:
    raise Error('Model type %s not supported' % name)

  args_dict['key_name'] = key_name
  
  model = getattr(db_models, '%sModel' % name)(**args_dict)
  if config.USE_MEMCACHE:
    memcache.set(key_name, value=model)
  if async:
    return (model, db.put_async(model))
  model.put()
  return model

 
def DeactivateActivityModel(model, reason, recurse=True):
  model.active = False
  model.deactivated_reason = reason
  model.put()
  if config.USE_MEMCACHE:
    memcache.delete(model.key().name())
  if recurse:
    for member_object in dir(model):
      if member_object.startswith('productmetriclog'):
        continue
      if member_object.endswith('model_set'):
        for child_model in getattr(model, member_object):
          try:
            DeactivateActivityModel(child_model, reason)
          except TypeError:
            logging.exception('parent_model key: %s child_model key: %s' %
                             (model.key().name(), child_model.key().name()))

def LogMetric(user_section, action):
  metric = db_models.ProductMetricLogModel(user_section=user_section,
                                           action=action)
  metric.put()
