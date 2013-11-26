import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

# TODO: Remove debug parts
# TODO: Error handling

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

# We set a parent key on the 'Greetings' to ensure that they are all in the same
# entity group. Queries across the single entity group will be consistent.
# However, the write rate should be limited to ~1/second.

def device_key(device_id):
	"""Constructs a Datastore key for a Device entity with device_id."""
	return ndb.Key('Device', device_id)

class SGUser(ndb.Model):
	"""Models a user entry with user, and device_id."""
	user = ndb.UserProperty()
	device_id = ndb.StringProperty()

class Observation(ndb.Model):
	"""Models an individual Observation entry with date, sample voltage, and amperage."""
	date = ndb.DateTimeProperty(auto_now_add=True)
	voltage = ndb.FloatProperty()
	amperage = ndb.FloatProperty()


class MainPage(webapp2.RequestHandler):

	def get(self):
		# TODO: Use cursor
		guser = users.get_current_user()

		if not(guser):
			self.redirect('/login')
			return

		sguser_query = SGUser.query(SGUser.user == guser)
		sgusers = sguser_query.fetch()

		if sgusers:
			sguser = sgusers[0]
		else:
			self.redirect('/signup')
			return

		device_id = sguser.device_id
		observation_query = Observation.query(ancestor=device_key(device_id)).order(-Observation.date)
		observations = observation_query.fetch(10)
	
		url = users.create_logout_url(self.request.uri)
		url_linktext = 'Logout'
	
		template_values = {
			'observations': observations,
			'device_id': urllib.quote_plus(device_id),
			'user_email': guser.email(),
			'url': url,
			'url_linktext': url_linktext,
		}

		template = JINJA_ENVIRONMENT.get_template('index.html')
		self.response.write(template.render(template_values))

class Update(webapp2.RequestHandler):

	# TODO: Authentication
	def post(self):
		# We set the same parent key on the 'Observation' to ensure each Observation is in
		# the same entity group. Queries across the single entity group will be consistent.
		# However, the write rate to a single entity group should be limited to ~1/second.

		device_id = self.request.get('device_id')
		observation = Observation(parent=device_key(device_id))
		
		observation.voltage = float(self.request.get('v'))
		observation.amperage = float(self.request.get('i'))
		observation.put()
		
		self.redirect('/')

class Login(webapp2.RequestHandler):

	def get(self):
		url = users.create_login_url('/')
		url_linktext = 'Login'
		template_values = {
			'url': url,
			'url_linktext': url_linktext
		}
		template = JINJA_ENVIRONMENT.get_template('login.html')
		self.response.write(template.render(template_values))

class Signup(webapp2.RequestHandler):

	def get(self):
		guser = users.get_current_user()

		if not(guser):
			self.redirect('/login')
			return

		user_email = guser.email()
		url = users.create_logout_url(self.request.uri)
		url_linktext = 'Logout'
		template_values = {
			'user_email': user_email,
			'url': url,
			'url_linktext': url_linktext
		}
		template = JINJA_ENVIRONMENT.get_template('signup.html')
		self.response.write(template.render(template_values))

	def post(self):
		sguser = SGUser()
		sguser.user = users.get_current_user()
		sguser.device_id = self.request.get('device_id')
		sguser.put()
		self.redirect('/')

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/update', Update),
    ('/login', Login),
    ('/signup', Signup),
], debug = True)

