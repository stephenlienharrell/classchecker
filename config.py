import os
import braintree
from google.appengine.api import app_identity


APP_NAME = 'App Title'

APP_TAGLINE = ('This app is Good!<br />'
              'really good!')

APP_DESCRIPTION = ('Stuff happens and you get classy')
             
ADMIN_EMAIL = 'classcheckeradmin@gmail.com'

TESTERS = ['free@forthisperson.com']

SUPPORTED_SCHOOLS = {
#### US Schools #####
    'Brown University': 
        {'enrollment': 8649,
         'base_url': 'https://selfservice.brown.edu/ss/'},
    'Georgia Institute of Technology':
        {'enrollment': 20487,
         'base_url': 'https://oscar.gatech.edu/pls/bprod/'},
    'University of Montana': 
        {'enrollment': 15642,
         'base_url': 'https://webprocess.umt.edu/cyberbear/'},
    'University of North Carolina at Charlotte':
        {'enrollment': 24700,
         'base_url': 'https://selfservice.uncc.edu/pls/BANPROD/'},
    'Radford University':
        {'enrollment': 8878,
         'base_url': 'https://ssb.radford.edu/PROD/'},
    'Thomas Jefferson University':
        {'enrollment': 2600,
         'base_url': 'https://banner.jefferson.edu/pls/tju/'},
    'University of Toledo':
        {'enrollment': 23336, 
         'base_url': 'https://selfservice.utoledo.edu/prod/'},
    'Austin Peay State University':
        {'enrollment': 10000,
         'base_url': 'https://apbrss2.apsu.edu/pls/PROD/'},
    'Canisius College':
        {'enrollment': 5000,
         'base_url': 'https://asterope.canisius.edu/pls/prod/'},
    'Lansing Community College':
        {'enrollment': 20394,
         'base_url': 'https://starnetb.lcc.edu/LCCB/'},
    'The Alamo Colleges':
        {'enrollment': 100000,
         'base_url': 'https://phoenixss.alamo.edu:4445/PROD/'},
    'Edison State College':
        {'enrollment': 17000,
         'base_url': 'https://oas.edison.edu/pls/PROD/'},
    'Central State University':
        {'enrollment': 2798,
         'base_url': 'https://wolf.ces.edu/ssbprd/'},
    'Tennessee Technological University':
        {'enrollment': 8918,
         'base_url': 'https://tturedss1.tntech.edu/pls/PROD/'},
    'State University of New York at Potsdam':
        {'enrollment': 3580, 
         'base_url': 'https://services.potsdam.edu/prod/'},
    'Southern Illinois University Carbondale':
        {'enrollment': 20350, 
         'base_url': 'https://opal.rocks.siu.edu/prod/'},
    'University of Alabama at Birmingham':
        {'enrollment': 18703, 
         'base_url': 'https://ssb.it.uab.edu/pls/sctprod/'},
    'College of Saint Benedict and Saint Johns University':
        {'enrollment': 3966, 
         'base_url': 'https://ssb.csbsju.edu/proddad/'},
    'University of New England':
        {'enrollment': 3167,
         'base_url': 'https://neem.une.edu/pls/prod/'},
    'Purdue University': 
        {'base_url': 'https://selfservice.mypurdue.purdue.edu/prod/'},
    'Purdue University Calumet': 
        {'base_url': 'https://banwebf.purduecal.edu/pls/proddad/'},


    'University of Oklahoma': 
        {'base_url': 'https://ssb.ou.edu/pls/PROD/'},
    'University of Tennessee at Martin': 
        {'base_url': 'https://banner.utm.edu/prod/'},
    'Colorado School of Mines': 
        {'base_url': 'https://banner.mines.edu/prod/owa/'},
    'Xavier University': 
        {'base_url': 'https://banner8ssb.xavier.edu:7777/PROD/'},
    'College of William and Mary': 
        {'base_url': 'https://banweb.wm.edu/pls/PROD/'},
    'Regent University': 
        {'base_url': 'https://genisys.regent.edu/pls/prod/'},
    'Southern Illinois Universty at Edwardsville': 
        {'base_url': 'https://ssb.siue.edu/pls/BANPROD/'},
    'NorthWest Arkansas Community College': 
        {'base_url': 'https://www2.nwacc.edu/dbServerNPROD/'},
    'Weber State University': 
        {'base_url': 'https://selfservice.weber.edu/pls/proddad/'},
    'Longwood University': 
        {'base_url': 'https://sequoia.longwood.edu/bnr8prod/'},
    'Wheaton College': 
        {'base_url': 'https://bannerweb.wheaton.edu/db1/'},
    'Northeastern University': 
        {'base_url': 'https://bnr8ssbp.neu.edu/udcprod8/'},

    'Auburn University': 
        {'base_url': 'https://banssb.prod.auburn.edu/pls/PROD/'},
    'University of the Pacific': 
        {'base_url': 'https://bssprd.pacific.edu:1532/owaprod/'},
    'Idaho State University': 
        {'base_url': 'https://ssb.isu.edu/bprod/'},
    'Auburn Montgomery': 
        {'base_url': 'https://senator.aum.edu/prod/'},
    'Kennesaw State University': 
        {'base_url': 'https://owlexpress.kennesaw.edu/prodban/'},
    'Temple University': 
        {'base_url': 'https://prd-ssb.temple.edu/prod8/'},
    'Spelman College': 
        {'base_url': 'https://banner-web.spelman.edu/pls/prod/'},
    'Ramapo College': 
        {'base_url': 'https://ssb-1.ramapo.edu/RCNJ/'},
    'University of San Diego':
        {'base_url': 'https://usdssb.sandiego.edu/prod/'},
    'Texas Tech University':
        {'base_url': 'https://ssb.texastech.edu/pls/TTUSPRD/'},
    'Ivy Tech Community College':
        {'base_url': 'https://banprod-ssb.ivytech.edu/BANNER/'},

    #### Many more with the Google Search "Dynamic Schedule"

                    }

FACEBOOK_PAGE = 'http://www.facebook.com/myawesomepage/qwerty'

REMOVE_WHITESPACE = True

USE_MEMCACHE = True

DEFAULT_TIMEZONE = 'US/Eastern'


#### If you change this you have to change the cron.yaml for the check ####
CLASS_CHECK_INTERVAL = 660.0

MINIMUM_TIME_BETWEEN_CHECKS = 7

PADDING_BEFORE_RECHECK = 60.0

EMAIL_NOTIFY_SLOTS = 3

DEACTIVATE_ERRORS = {'NOSCHOOL': 'School no longer supported',
                     'NOTERM': 'Term no longer available',
                     'NOCLASS': 'Class no longer found',
                     'USEROFF': 'Class deactivated by user',
                     'NOGATEWAY': 'Gateway deactivated.'}

CONTACT_EMAIL = 'info@classtastic.com'

TEMPLATE_DIRECTORY = 'templates'

TERM_PAGE = 'bwckschd.p_disp_dyn_sched'

CLASS_PAGE = ('bwckschd.p_disp_detail_sched?term_in=%(term_number)s&crn_in='
              '%(section_number)s')

SECURE_AJAX_URL = 'https://%s-dot-%s.appspot.com' % (str(os.environ['CURRENT_VERSION_ID']).split('.')[0], 
                                                             app_identity.get_application_id())

DEFAULT_SECTION_COST = 5
DEFAULT_SECTION_COST_BTC = 0.005

ADWORDS_CONVERSION_BEACON = 'https://www.googleadservices.com/pagead/conversion/somenumber_and_things'

## Current limit of how many tasks can be added at one
## is 100, play it safe with 90
QUEUE_ADD_LIMIT = 90

PROMO_CODE_REASONS = ['freebie', 'friend', 'work_trade']

PROMO_CODE_TYPES = ['single', 'multi']

METRIC_ACTIONS = ['user_deactivated_class', 'purchased_google_checkout',
                  'purchased_promo_code', 'cart_sent_google_checkout',
                  'class_added_to_ui', 'seat_available_notify',
                  'waitlist_notify', 'class_no_longer_found_notify',
                  'waiting_for_bitcoin_payment', 'bitcoin_payment_received',
                  'credit_card_charged']

BLOCKCHAIN_INFO_SECRET = 'somesecret'

#the values better add up to 1.0 because I'm not checking anywhere else
DESKTOP_WALLET_BITCOIN_ADDRESS_DICT = {
    '17TYtsanoBrTfFFDpkH7K5XfLvyYm88ttq': 1, # ClassChecker Author Bitcoin Address :)
}

BITCOIN_TRANSACTION_FEE = 0.0001
BLOCKCHAIN_INFO_BITCOIN_ADDRESS = '1MfS9Xbd7qprsomeadddress'
BLOCKCHAIN_INFO_WALLET_GUID = '2daa0837-3e86-someguid'
BLOCKCHAIN_INFO_PASSWORD = 'somepassword'
BLOCKCHAIN_INFO_SECOND_PASSWORD = 'otherpassword'

BRAINTREE_SANDBOX = False

if BRAINTREE_SANDBOX:
  BRAINTREE_ENVIRONMENT = braintree.Environment.Sandbox
  BRAINTREE_MERCHANT_ID = 'mymerchantid'
  BRAINTREE_PUBLIC_KEY = 'merchantpublickey'
  BRAINTREE_PRIVATE_KEY = 'merchantprivatekey'
  BRAINTREE_JS_ENCRYPTION_KEY = 'jsencryptkey'
else:
  BRAINTREE_ENVIRONMENT = braintree.Environment.Production
  BRAINTREE_MERCHANT_ID = 'mymerchantid'
  BRAINTREE_PUBLIC_KEY = 'merchantpublickey'
  BRAINTREE_PRIVATE_KEY = 'merchantprivatekey'
  BRAINTREE_JS_ENCRYPTION_KEY = 'jsencryptkey'

