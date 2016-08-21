import datetime
import logging
from operator import itemgetter
import os
from PyRSS2Gen import PyRSS2Gen
import re

import jinja2

import base_handler
import config
import press_releases

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),
                                   config.TEMPLATE_DIRECTORY)))

class PressPage(base_handler.BaseRequestHandler):

  def NotFound(self):
    self.error(404)
    template_values = {'app_name': config.APP_NAME,
                       'year': datetime.datetime.now().year,}
    template = jinja_environment.get_template('404.html')
    page = template.render(template_values)

    if config.REMOVE_WHITESPACE == True:
      page = re.sub(">\s*<","><", page)
    self.response.out.write(page)

  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    release_list = sorted(press_releases.RELEASE_LIST, key=itemgetter('date'),
                          reverse=True)
    url_list = []
    html_links = []
    for index, release in enumerate(release_list):
      url = '%s_%s' % (release['date'],
                       re.sub('\W', '', release['title']))
      url_list.append(url)
      release_list[index]['url'] = url
      html_links.append('<a href="%s">%s - %s</a>' % (url, release['title'],
                                                      release['date']))
      
    current_url = self.request.url.split('/')[-1] 
    if not current_url in url_list and current_url != 'current':
      self.NotFound()
      return

    if current_url == 'current':
      current_url = url_list[0]

    for release in release_list:
      if release['url'] == current_url:
        break
    
    

    template_values = {'app_name': config.APP_NAME,
                       'press_links': '</li><li>'.join(html_links),
                       'release_title': release['title'],
                       'release_text': release['release_text'],
                       'year': datetime.datetime.now().year,
                       'contact_email': config.CONTACT_EMAIL,}
                         
    template = jinja_environment.get_template('press.html')
    page = template.render(template_values)

    if config.REMOVE_WHITESPACE == True:
      page = re.sub(">\s*<","><", page)
    self.response.out.write(page)

class PressRssFeed(base_handler.BaseRequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'application/rss+xml'
    release_list = sorted(press_releases.RELEASE_LIST, key=itemgetter('date'),
                          reverse=True)
    item_list = []
    for release in release_list:
      url = '%s_%s' % (release['date'],
                       re.sub('\W', '', release['title']))
      url = '%s%s' % ('http://www.classtastic.com/press/', url) 
      rss_item = PyRSS2Gen.RSSItem(title = release['title'], link = url,
                                   description = release['description'],
                                   guid = PyRSS2Gen.Guid(url),
                                   pubDate = datetime.datetime(2003, 9, 6))
 
      item_list.append(rss_item)

    rss = PyRSS2Gen.RSS2(title="ClassChecker! Press Releases",
                         link="http://www.classtastic.com/press/rss.xml",
                         description="The latest press releases from ClassChecker!",
                         lastBuildDate = datetime.datetime.utcnow(),
                         items = item_list)

    self.response.out.write(rss.to_xml())
    
