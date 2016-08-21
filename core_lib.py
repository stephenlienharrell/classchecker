import ConfigParser
import datetime
import logging
import random
import re
import sys
import time

from google.appengine.api import urlfetch
from google.appengine.ext import ereporter

ereporter.register_logger()

from googlevoice import Voice
from googlevoice.util import input as voice_input
import config
import db_lib
import db_models


class Error(Exception):
  pass

class ReturnCodeWasNot200(Error):
  pass


class ClassPageNotParsableError(Error):
  pass

class ProgramingError(Error):
  pass
  
def FetchClassAndUpdateSection(school_name, term_number, section_number,
                               term_name=None):
  start_time = time.time()
  school_name = school_name.replace('_', ' ')
  section_url = '%s%s' % (
          config.SUPPORTED_SCHOOLS[school_name]['base_url'],
          config.CLASS_PAGE % {'term_number': term_number,
                               'section_number': section_number})
  rpc = urlfetch.create_rpc(deadline=10)
  headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.66 Safari/535.11'}
  urlfetch.make_fetch_call(rpc, section_url, headers=headers)

  section_key = section_key_name = '%s%s%s' % (school_name, term_number,
                                               section_number)
  section = db_lib.GetModelByKeyName('Section', section_key)

  previous_remaining = None

  if section is None:
    term = db_lib.GetModelByKeyName('Term', '%s%s' % (school_name,
                                                      term_number))
  else:
    previous_remaining = section.seats_available

  last_checked = datetime.datetime.utcnow()
  try:
    result = rpc.get_result()
  except urlfetch.Error as e:
    logging.exception('Unable to fetch ' + section_url)
    raise type(e), type(e)(e.message + '\nUnable to fetch ' + section_url), sys.exc_info()[2]

  # this is wonky and I hope to figure out a better way to do this since I always catch this and urlfetch
  # errors together and assume the exception has already been logged, this seems to be the easiest way
  # to make sure it is logged
  if result.status_code != 200:
    try: 
      raise ReturnCodeWasNot200('Page fetch: %s\n  status was not 200: %s' % (section_url,
                                                                              result.status_code))
    except ReturnCodeWasNot200, error_message:
      if result.status_code == 404:
        logging.exception('File not found')
      else:
        logging.error(error_message)
      raise

  try:
    class_info = CheckClass(result, section_number)
  except ClassPageNotParsableError:
    logging.exception('Unparsable URL: %s' % section_url)
    raise

  if section is None:
    section_params = {'term': term,
                      'section_number': int(section_number),
                      'last_checked': last_checked,
                      'class_title': class_info['class_title'],
                      'class_number': class_info['class_number'],
                      'seats_available': class_info['remaining'],
                      'seats_total': class_info['capacity']}
    if 'waitlist_capacity' in class_info:
      section_params['waitlist_seats_available'] = class_info[
          'waitlist_capacity']
      section_params['waitlist_seats_total'] = class_info[
          'waitlist_remaining']

    section = db_lib.CreateModel('Section', section_params)

  else:
    section.seats_available = class_info['remaining']
    section.class_title = class_info['class_title']
    section.class_number = class_info['class_number']
    section.seats_total = class_info['capacity']
    section.remaining = class_info['remaining']
    section.last_checked = last_checked

    if 'waitlist_capacity' in class_info:
      old_waitlist_seats_total = section.waitlist_seats_total
      section.waitlist_seats_available = class_info['waitlist_capacity']
      section.waitlist_seats_total = class_info['waitlist_remaining']

#      #dude how am I supposed to test this?
#      if old_waitlist_seats_total == 0 and section.waitlist_seats_total > 0:
#        user_sections = db_lib.GetReferenceSet('UserSection', 'Section', 'section',
#                                               section.key().name(),
#                                               {'active': True, 'paid': True,
#                                                'pending_transaction': False})
#        for user_section in user_sections:
#          if not user_section.last_notified:
#            user_promo_code = CreatePromoCode('single', 'waitlisted_class', 1, user_section.user)
#            #fire_email(user_section.user, user_promo_code)
#            user_section.active = False
#            db_lib.UpdateModel(user_section)

    ## code to stop indexing and reduce write ops on currently running sections
    #section._unindexed_properties = frozenset(['waitlist_seats_available', 'seats_available', 'seats_total', 'waitlist_seats_total', 'last_checked'])

    db_lib.UpdateModel(section)

  if term_name is None:
    term_name = term_number

  log_message = ('Class: %s at %s in %s\nPrevious seats remaining: %s; '
                 'Seats remaining: %s\n' % 
                (section_number, school_name, term_name,
                 previous_remaining, section.seats_available))

  if 'waitlist_capacity' in class_info:
    log_message += ('Waitlist seats available: %s; '
                   'Waitlist seats remaining: %s\n' %
                   (class_info['waitlist_capacity'],
                    class_info['waitlist_remaining']))

  log_message += 'Check time: %s seconds' % (time.time() - start_time)

  logging.info(log_message)


  return section, previous_remaining


def CheckClass(response, section_number):
  seats_found = False
  wait_seats_found = False
  cross_seats_found = False
  seat_numbers_found = 0
  wait_seat_numbers_found = 0
  cross_seat_numbers_found = 0


  if response.content.find(str(section_number)) == -1:
    raise ClassPageNotParsableError('Unable to find section number on page')

  for line in response.content.split('\n'):
    if line.find(str(section_number)) > -1:
      class_title = line.rsplit('-', 3)[0].split('>')[-1].strip()
      class_number = line.rsplit('-', 3)[2].strip()
      continue

    if line.find('>Seats') > -1:
      seats_found = True
      continue
    if seats_found == True:
      if seat_numbers_found == 0:
        capacity = line.split('>')[1].split('<')[0]
        if capacity.replace('-', '').isdigit():
          seat_numbers_found += 1
        continue
      elif seat_numbers_found == 1:
        actual = line.split('>')[1].split('<')[0]
        if actual.replace('-', '').isdigit():
          seat_numbers_found += 1
        continue
      elif seat_numbers_found == 2:
        remaining = line.split('>')[1].split('<')[0]
        if remaining.replace('-', '').isdigit():
          seat_numbers_found += 1

    if line.find('>Waitlist Seats') > -1:
      wait_seats_found = True
      continue

    if wait_seats_found == True:
      if wait_seat_numbers_found == 0:
        wait_capacity = line.split('>')[1].split('<')[0]
        if wait_capacity.replace('-', '').isdigit():
          wait_seat_numbers_found += 1
        continue
      elif wait_seat_numbers_found == 1:
        wait_actual = line.split('>')[1].split('<')[0]
        if wait_actual.replace('-', '').isdigit():
          wait_seat_numbers_found += 1
        continue
      elif wait_seat_numbers_found == 2:
        wait_remaining = line.split('>')[1].split('<')[0]
        if wait_remaining.replace('-', '').isdigit():
          wait_seat_numbers_found += 1

    if line.find('>Cross List Seats') > -1:
      cross_seats_found = True
      continue

    if cross_seats_found == True:
      if cross_seat_numbers_found == 0:
        cross_capacity = line.split('>')[1].split('<')[0]
        if cross_capacity.replace('-', '').isdigit():
          cross_seat_numbers_found += 1
        continue
      elif cross_seat_numbers_found == 1:
        cross_actual = line.split('>')[1].split('<')[0]
        if cross_actual.replace('-', '').isdigit():
          cross_seat_numbers_found += 1
        continue
      elif cross_seat_numbers_found == 2:
        cross_remaining = line.split('>')[1].split('<')[0]
        if cross_remaining.replace('-', '').isdigit():
          cross_seat_numbers_found += 1
          break

  if seat_numbers_found != 3:
    raise ClassPageNotParsableError('Could not parse section %s' %
                                    section_number)

  class_info_dict = {'capacity': int(capacity), 'remaining': int(remaining),
                     'class_title': class_title, 'class_number': class_number}
  if wait_seats_found == True and wait_seat_numbers_found == 3:
    class_info_dict['waitlist_capacity'] = int(wait_capacity)
    class_info_dict['waitlist_remaining'] = int(wait_remaining)

  if cross_seats_found == True and cross_seat_numbers_found == 3:
    class_info_dict['capacity'] = int(cross_capacity)
    class_info_dict['remaining'] = int(cross_remaining)

  return class_info_dict


def GetCurrentTerms(response):

  terms = {}
  for line in response.content.split('\n'):
    if line.find('OPTION') > -1:
      term_name = line.split('>')[1].split('<')[0]
      term_number = line.split('>')[0].split('=')[-1].strip('"')
      if term_name.lower().endswith('(view only)'):
        continue
      if term_number:
        terms[term_name] = term_number
  
  return terms

def CreatePromoCode(type, reason, uses=None, user=None):
  promo_code_dict = {}
  system_random = random.SystemRandom()
  promo_code = ''.join(system_random.sample(
      'ABCDEFGHJKLMNPQRTUVWXY346789', 12))
  promo_code_dict['code'] = promo_code
  promo_code_dict['type'] = type
  promo_code_dict['reason'] = reason
  promo_code_dict['user'] = user
  promo_code_dict['uses_left'] = uses

  if user is None and uses > 1:
    raise ProgramingError('Codes for multiple classes must have a user '
                          'atattched')
  db_lib.CreateModel('PromoCode', promo_code_dict)
  return promo_code

def SendSMS(phone_number, message):
  voice = Voice()
  voice.login()
  voice.send_sms(phone_number, message)

def GetPaymentPrice(user_section):
  return config.DEFAULT_SECTION_COST
