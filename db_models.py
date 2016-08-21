from google.appengine.ext import db

import config

class BaseModel(db.Model):
  def get_key_from_reference(self, property_name):
    return getattr(self.__class__, property_name).get_value_for_datastore(self)

class UserModel(BaseModel):
  active = db.BooleanProperty(default=True)
  deactived_reason = db.StringProperty(
      choices=set(config.DEACTIVATE_ERRORS.values()))
  user = db.UserProperty(required=True)
  primary_email = db.EmailProperty(required=True)
  gtalk_id = db.EmailProperty(indexed=False)
  cell_phone = db.PhoneNumberProperty(indexed=False)
  timezone = db.StringProperty()

class SchoolModel(BaseModel):
  active = db.BooleanProperty(default=True)
  deactived_reason = db.StringProperty(
      choices=set(config.DEACTIVATE_ERRORS.values()))
  school_name = db.StringProperty(required=True)
  base_url = db.LinkProperty(required=True, indexed=False)

class UserCurrentSchoolModel(BaseModel):
  active = db.BooleanProperty(default=True)
  deactived_reason = db.StringProperty(
      choices=set(config.DEACTIVATE_ERRORS.values()))
  user = db.ReferenceProperty(UserModel, required=True)
  school = db.ReferenceProperty(SchoolModel, required=True)

class TermModel(BaseModel):
  active = db.BooleanProperty(default=True)
  deactived_reason = db.StringProperty(
      choices=set(config.DEACTIVATE_ERRORS.values()))
  term_name = db.StringProperty(required=True)
  term_number = db.IntegerProperty(required=True, indexed=False)
  school = db.ReferenceProperty(SchoolModel, required=True)

class SectionModel(BaseModel):
  active = db.BooleanProperty(default=True)
  deactived_reason = db.StringProperty(
      choices=set(config.DEACTIVATE_ERRORS.values()))
  term = db.ReferenceProperty(TermModel, required=True)
  section_number = db.IntegerProperty(required=True)
  class_title = db.StringProperty(required=True)
  class_number = db.StringProperty(required=True)
  last_checked = db.DateTimeProperty(auto_now=True, indexed=False)
  seats_available = db.IntegerProperty(required=True, indexed=False)
  seats_total = db.IntegerProperty(required=True, indexed=False)
  waitlist_seats_available = db.IntegerProperty(indexed=False)
  waitlist_seats_total = db.IntegerProperty(indexed=False)

class TransactionModel(BaseModel):
  charge_date = db.DateTimeProperty()
  created_date = db.DateTimeProperty(auto_now_add=True)
  errors = db.TextProperty()  
  order_number = db.StringProperty()
  transaction_email = db.EmailProperty()
  total_charge_amount = db.FloatProperty()
  user = db.ReferenceProperty(UserModel, required=True)
  btc_address = db.StringProperty() #where they had to send btc to
  total_satoshi_amount = db.IntegerProperty() #how much they had to send
  input_tx_hash = db.StringProperty() #user's btc -> blockchain redirecter
  output_tx_hash = db.StringProperty() #blockchain -> config.BITCOIN_ADDRESS

class UserSectionModel(BaseModel):
  active = db.BooleanProperty(default=True)
  deactived_reason = db.StringProperty(
      choices=set(config.DEACTIVATE_ERRORS.values()))
  section = db.ReferenceProperty(SectionModel, required=True)
  school = db.ReferenceProperty(SchoolModel, required=True)
  user = db.ReferenceProperty(UserModel, required=True)
  paid = db.BooleanProperty(default=False)
  transaction = db.ReferenceProperty(TransactionModel)
  pending_transaction = db.BooleanProperty(default=False)
  created = db.DateTimeProperty(auto_now_add=True)
  last_notified = db.DateTimeProperty()

class PendingTransactionModel(BaseModel):
  created_date = db.DateTimeProperty(auto_now_add=True)
  order_number = db.StringProperty() #bitcoin address
  total_satoshi_amount = db.IntegerProperty() #how much we're expecting in satoshi
  total_dollar_amount = db.FloatProperty() #how much we're expecting in USD
  transaction_email = db.EmailProperty()
  user = db.ReferenceProperty(UserModel, required=True)
  user_section_list = db.StringListProperty(required=True)

class PromoCodeModel(BaseModel):
  active = db.BooleanProperty(default=True)
  reason = db.StringProperty(
    choices=set(config.PROMO_CODE_REASONS))
  type = db.StringProperty(
    choices=set(config.PROMO_CODE_TYPES))
  code = db.StringProperty(required=True)
  uses_left = db.IntegerProperty(default=1)
  user = db.ReferenceProperty(UserModel)
  date = db.DateTimeProperty(auto_now_add=True)

class ProductMetricLogModel(BaseModel):
  user_section = db.ReferenceProperty(UserSectionModel, required=True)
  action = db.StringProperty(
    choices=set(config.METRIC_ACTIONS))
  date = db.DateTimeProperty(auto_now_add=True)
