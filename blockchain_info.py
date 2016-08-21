import datetime
import logging
import urllib
import os

from google.appengine.api import mail
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.runtime import DeadlineExceededError 

import json
import jinja2

import base_handler
import config
import db_lib
import db_models

def SendBitcoin(to_address, satoshi_amount):
  fee = toSatoshi(config.BITCOIN_TRANSACTION_FEE)
  satoshi_amount -= fee 

  if satoshi_amount <= 0:
    return False

  root_url = 'https://blockchain.info/merchant/%s/payment' % config.BLOCKCHAIN_INFO_WALLET_GUID
  url_args = urllib.urlencode({
    'password': config.BLOCKCHAIN_INFO_PASSWORD,
    'second_password': config.BLOCKCHAIN_INFO_SECOND_PASSWORD,
    'to': to_address,
    'amount': satoshi_amount,
    'fee': fee,
  })

  try:
    response = urlfetch.fetch('%s?%s' % (root_url, url_args), deadline=60).content
    logging.info(response)
    return json.loads(response)
  except DeadlineExceededError:
    pass

#address_dict is a dictionary that maps btc_address: satoshi_amount
def DistributeBitcoinPayment(satoshi_amount):
  fee = toSatoshi(config.BITCOIN_TRANSACTION_FEE)
  satoshi_amount -= fee 

  if satoshi_amount <= 0:
    return False

  #calculate how much everyone gets
  btc_address_to_amount_dict = {}
  total = 0
  for address, percentage in config.DESKTOP_WALLET_BITCOIN_ADDRESS_DICT.items():
    total += int(satoshi_amount * percentage)
    btc_address_to_amount_dict[address] = int(satoshi_amount * percentage)
  
  btc_address_to_amount_dict[btc_address_to_amount_dict.keys()[0]] += (satoshi_amount - total)
  logging.info('Sending satoshis to: %s' %  btc_address_to_amount_dict)

  root_url = 'https://blockchain.info/merchant/%s/sendmany' % config.BLOCKCHAIN_INFO_WALLET_GUID
  url_args = urllib.urlencode({
    'password': config.BLOCKCHAIN_INFO_PASSWORD,
    'second_password': config.BLOCKCHAIN_INFO_SECOND_PASSWORD,
    'recipients': json.dumps(btc_address_to_amount_dict),
    'fee': fee,
  })
  
  try:
    response = urlfetch.fetch('%s?%s' % (root_url, url_args), deadline=60).content
    logging.info(response)
    return json.loads(response)
  except DeadlineExceededError:
    pass
  pass

def GetBitcoinAddress():
  root_url = 'http://blockchain.info/api/receive'
  url_args = urllib.urlencode({
    'method': 'create',
    'address': config.BLOCKCHAIN_INFO_BITCOIN_ADDRESS,
    'callback': '%s/blockchain_notify?secret=%s' % (config.SECURE_AJAX_URL, config.BLOCKCHAIN_INFO_SECRET),
  })

  response = urlfetch.fetch('%s?%s' % (root_url, url_args)).content
  return json.loads(response)['input_address']

#float - 1.23 meaning $1.23
def GetBitcoinAmount(dollar_amount):
  return urlfetch.fetch('http://blockchain.info/tobtc?currency=USD&value=%s' % dollar_amount).content

def GetSendingAddress(tx_hash):
  url = 'https://blockchain.info/tx-index/%s?format=json' % tx_hash
  response = urlfetch.fetch(url).content
  response_dict = json.loads(response)
  inputs = response_dict['inputs']
  tx_input = inputs[0]
  input_address = tx_input['prev_out']['addr'] 

  return input_address

#amount is in satoshi
def HandleBlockchainCallback(input_address, amount, input_tx, output_tx, secret):
  if secret != config.BLOCKCHAIN_INFO_SECRET:
    #someone is trying to con us
    return

  customer_address = GetSendingAddress(input_tx)
  logging.info('just got a payment of %s from %s' % (amount, customer_address))
  order_number = input_address #hackstorm
  pending_transaction = db_models.PendingTransactionModel.all().filter(
      'order_number =', order_number).get()

  if pending_transaction is None:
    #wot. this could be serious. someone sent us money and we don't know wtf to do with it...
    #let's just send it back?
    logging.info('%s sent us %s but idk who he is' % (customer_address, amount))
    SendBitcoin(customer_address, amount)
    return False

  extra_paid = amount - pending_transaction.total_satoshi_amount
  if extra_paid < 0:
    #they did not send us enough money...wut
    #let's just send it back?
    logging.info('%s sent too little - %s - were supposed to send %s' % (customer_address, amount, pending_transaction.total_satoshi_amount))
    SendBitcoin(customer_address, amount)
    return False
  elif extra_paid > 0:
    logging.info('%s sent too much - %s - were supposed to send %s' % (customer_address, amount, pending_transaction.total_satoshi_amount))
    SendBitcoin(customer_address, extra_paid)

  #Get it out of Blockchain.info wallet. idk if I trust it too much
  DistributeBitcoinPayment(pending_transaction.total_satoshi_amount)

  transaction = db_lib.CreateModel('Transaction', {
      'order_number': order_number,
      'transaction_email': pending_transaction.transaction_email, 
      'user': pending_transaction.user,
      'total_charge_amount': pending_transaction.total_dollar_amount,
      'total_satoshi_amount': amount,
      'btc_address': customer_address,
      'input_tx_hash': input_tx,
      'output_tx_hash': output_tx,
      'created_date': datetime.datetime.utcnow(),
  })

  jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                   config.TEMPLATE_DIRECTORY)))

  sections_list = []
  for user_section_key in pending_transaction.user_section_list:
    user_section = db_lib.GetModelByKeyName('UserSection', user_section_key)
    user_section.transaction = transaction
    user_section.paid = True
    user_section.pending_transaction = False
    sections_list.append(str(user_section.section.section_number))

    db_lib.UpdateModel(user_section)

  school = user_section.school.school_name
  user = user_section.user
  sender_address = 'ClassChecker! Automated Notifier <info@classtastic.com>' 
  subject = 'Notifications active on ClassChecker!'
  template_values = {'school': school,
                     'sections_list_string': ','.join(sections_list)}
  text_path = os.path.join(os.path.dirname(__file__),
                           config.TEMPLATE_DIRECTORY,
                           'email_bitcoin_notify.txt')
  message = mail.EmailMessage(sender=sender_address, subject=subject)
  message.to = user.primary_email
  text_portion = open(text_path, 'r').read() % template_values
  message.body = text_portion
  template = jinja_environment.get_template('email_bitcoin_notify.html')
  message.html = template.render(template_values)
  try:
    message.send()
    logging.info('Sent mail:\n%s' % text_portion)
  except Exception:
    logging.exception('Mail: %s to %s failed' % (text_portion, user.primary_email))

  db_lib.LogMetric(user_section, 'bitcoin_payment_received')

  memcache.delete('UserSectionListFor%s' %
      pending_transaction.user.user.user_id())

def toSatoshi(bitcoins):
  return int(float(bitcoins) * 100000000)

def fromSatoshi(satoshi):
  return '{:.8f}'.format(int(satoshi) / float(100000000))

#listens for blockchain.info callback
class BlockchainListener(base_handler.BaseRequestHandler):
  def get(self):
    try:
      input_address = self.request.get('input_address')
      satoshi_amount = int(self.request.get('value'))
      secret = self.request.get('secret')
      input_tx_hash = self.request.get('input_transaction_hash')
      output_tx_hash = self.request.get('transaction_hash')

      HandleBlockchainCallback(input_address, satoshi_amount, 
          input_tx_hash, output_tx_hash, secret)
    finally:
      #always write this out so blockchain.info knows we got it
      self.response.write('*ok*')

