#!/usr/bin/env python

import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.gen
import os.path
import uuid
import time
import json

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
			(r"/chatsocket", ChatSocketHandler),
			(r"/login", LoginHandler),
			(r"/logout", LogoutHandler),
		]
		settings = dict(
			cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			xsrf_cookies=True,
		)
		super(Application, self).__init__(handlers, **settings)
		
class LogoutHandler(tornado.web.RequestHandler):
	def get(self):
		self.clear_cookie("concordant_user")
		self.redirect(self.get_argument("next", "/"))


class MainHandler(tornado.web.RequestHandler):
	def get(self):
		user = self.get_secure_cookie("concordant_user");
		if (user != None):
			user = user.decode("utf-8")
			print(user)
			self.render("index.html", need_login=False)
		else:
			self.render("index.html", need_login=True)
		return

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
	waiters = set()
	rooms = {}
	cache = []
	cache_size = 200
	
	users = {}
	
	def get_current_user(self):
		user_cookie = self.get_secure_cookie("concordant_user")
		if user_cookie:
			return json.loads(user_cookie.decode("utf-8"))
		return None

	def get_compression_options(self):
		# Non-None enables compression with default options.
		return {}

	def open(self):
		# Add the username to the list if it hasnt been already
		name = self.current_user["name"]
		if ChatSocketHandler.users.get(name) == None:
			ChatSocketHandler.users[name] = 1
			ChatSocketHandler.add_user(name)
		else:
			ChatSocketHandler.users[name] = ChatSocketHandler.users[name] + 1
			
		ChatSocketHandler.waiters.add(self)
		
		# Send all connected users
		for user in ChatSocketHandler.users:
			self.write_message({"add_user": user})
		
		# Send the client all of the available rooms
		for room in ChatSocketHandler.rooms:
			self.write_message({"add_room": room, 
			                    "description": ChatSocketHandler.rooms[room]["description"] })
		
		
		# Send all past messages to the user for all of the rooms they are in
		# Lets assume this is all of them for now
		
		# Todo figure out a way to avoid sending 200*rooms messages at max
		# Basically need some kind of smart scrolling/loading and only to send
		# Relevant room messages to the client (keep track of what rooms the user
		# is in)
		for msg in ChatSocketHandler.cache:
			try:
				self.write_message(msg)
			except:
				logging.error("Error sending message", exc_info=True)
	
			
	def on_close(self):
		print("Closed")
		name = self.current_user["name"]
		
		ChatSocketHandler.users[name] = ChatSocketHandler.users[name] - 1
		if ChatSocketHandler.users[name] == 0:
			del ChatSocketHandler.users[name]
			ChatSocketHandler.remove_user(name)
			
		ChatSocketHandler.waiters.remove(self)
		
	@classmethod
	def add_room(cls, name, description):
		cls.rooms[name] = {
			"description": description,
			"cache": [],
			"cache_size": 200
		};
		
		cls.message("Welcome to " + name, "SYSTEM", name)

	@classmethod
	def update_cache(cls, room, chat):
		cls.cache.append(chat)
		if len(cls.cache) > cls.cache_size:
			cls.cache = cls.cache[-cls.cache_size:]

	@classmethod
	def send_updates(cls, chat):
	    # Todo send this only to users in these rooms
		logging.info("sending message to %d waiters", len(cls.waiters))
		for waiter in cls.waiters:
			try:
				waiter.write_message(chat)
			except:
				logging.error("Error sending message", exc_info=True)
		
	@classmethod
	def add_user(cls, name):
		for waiter in cls.waiters:
			try:
				waiter.write_message({"add_user": name})
			except:
				logging.error("Error sending message", exc_info=True)
				
	@classmethod
	def remove_user(cls, name):
		for waiter in cls.waiters:
			try:
				waiter.write_message({"remove_user": name})
			except:
				logging.error("Error sending message", exc_info=True)

	def on_message(self, message):
		logging.info("got message %r", message)
		parsed = tornado.escape.json_decode(message)
		if (parsed["body"] == ""):
			return#Ignore empty messages
			
		# Do rate limit here
		self.message(parsed["body"], self.current_user["name"], parsed["room"]);
	
	@classmethod
	def message(self, message, user, room_name):
		chat = {
			"id": str(uuid.uuid4()),
			"body": message,
			"user": user,
			"time": time.time(),
			"room": room_name
		}
		
		# Check that the room actually exists
		room = ChatSocketHandler.rooms[room_name]
		if room == None:
			logging.error("The room '" + room_name + "' does not exist, ignoring message")
			return
			
		chat["html"] = tornado.escape.linkify(message, extra_params='target="_blank"');
		ChatSocketHandler.update_cache(room, chat)
		ChatSocketHandler.send_updates(chat)

class LoginHandler(tornado.web.RequestHandler):
	async def get(self):
		# If there are no authors, redirect to the account creation page.
		self.render("login.html", error=None)

	async def post(self):
		data = {"name": self.get_argument("username")};
		self.set_secure_cookie("concordant_user", json.dumps(data))
		self.redirect(self.get_argument("next", "/"))
	

def main():
	tornado.options.parse_command_line()
	ChatSocketHandler.add_room("General", "Random Stuff")
	ChatSocketHandler.add_room("WAYWO", "What are YOU working on?")
	ChatSocketHandler.add_room("Programming-Help", "The helpful place.")
	app = Application()
	app.listen(options.port)
	tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
	main()
