# --- Josh Aaron Miller 2021
# --- Logger class to help organize debug output

import time

class Logger():

	def __init__(self, class_name):
		self.class_name = class_name
		
	def log(function, message):
		t = time.strftime("%m/%d/%Y, %H:%M:%S", time.localtime())
		print("[" + t + "] " + self.class_name + "." + function + ": " + message)