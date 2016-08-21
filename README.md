# ClassChecker
Seat checking for college courses that once ran on classtastic.com. Built for Google App Engine Python.

If you would like to run this software there a number of places I have anonmized this code. It will take some work to get going for someone else but it is here if you would like to try. This is provided for posterity but this project is no longer maintained. I have not attempted to upload this software to GAE since 2014 so YMMV.

The way that GAE does (or did) python dependencies was rather non-pythonic. I ended up having to unzip a number of dependencies into directories at the top level so they could be used. I will list them here, with the directory names and the version and URL if I know it (some I do not or no longer exist). It is possible that you can use different versions that I specify, I have only tested with these versions.

Directory: PyRSS2Gen
URL: https://pypi.python.org/pypi/PyRSS2Gen
Version: 1.0

Directory: googlevoice
URL: https://pypi.python.org/pypi/pygooglevoice/
Version: 0.5
Caveat: urlopen doesn't work correctly in GAE, please see this blog post for help: http://everydayscripting.blogspot.com/2009/08/google-app-engine-cookie-handling-with.html

Directory: braintree
URL: https://developers.braintreepayments.com/start/hello-server/python
Version: not specified
Caveat: I was using this before the Paypal buyout. YMMV

Directory: pytz
URL: https://github.com/brianmhunt/pytz-appengine
Version: Unlcear, 2010h?

Directory: requests
URL: http://docs.python-requests.org/en/master/
Version: 2.0.1
