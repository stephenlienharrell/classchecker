import logging

from google.appengine.ext import ereporter
import webapp2

from tasks_pages import *

ereporter.register_logger()

app = webapp2.WSGIApplication([
                               ('/tasks/update_schools',
                                   UpdateSchools),
                               ('/tasks/clear_all_user_section_list_caches',
                                    ClearAllUserSectionListCaches),
                               ('/tasks/show_memcache_stats',
                                    ShowMemcacheStats),
                               ('/tasks/promo_codes',
                                     PromoCodePage),
                               ('/tasks/deactivation_rechecker',
                                     DeactivationCheckerSchoolAndTerm),
                               ('/tasks/check_class_by_schools',
                                     CheckClassBySchools),
                               ('/tasks/check_class',
                                     CheckClass),
                               ('/tasks/email_class_info',
                                     EmailClassInfo),],
                               debug=True)
