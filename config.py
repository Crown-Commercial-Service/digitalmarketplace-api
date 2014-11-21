import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
	CONFIG_PROPERTY = "some_property"

	@staticmethod
	def init_app(app):
		pass

class Development(Config):
	DEBUG = True

class Live(Config):
	DEBUG = False

config = {
	'live' : Live,
	'development' : Development
}