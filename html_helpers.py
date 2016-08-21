from pytz.gae import pytz
import db_lib

def CreateTimezoneOptions():
  timezones = []
  for timezone in pytz.common_timezones:
    if timezone.startswith('US/'):
      timezones.append(timezone)
  timezones.extend(pytz.common_timezones)
  timezone_options = []
  for timezone in timezones:
    timezone_options.append('<option id="%s" value="%s">%s</option>' % (
        (timezone.replace('/', '_'), timezone, timezone)))
  return ''.join(timezone_options)
  
def CreateSchoolOptions():
  schools = db_lib.ListSchools()
  school_options = []
  for school in schools:
    school_options.append('<option id="%s" value="%s">%s</option>' % (
        school.replace(' ', '_'), school.replace(' ', '_'), school))
  return ''.join(school_options)

  

