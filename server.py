#!/usr/bin/env python

import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid
import time

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/chatsocket", ChatSocketHandler),
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        super(Application, self).__init__(handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")
        return

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    rooms = {
        "General": {
            "description": "Random Stuff",
            "cache": [],
            "cache_size": 200
        },
        "WAYWO": {
            "description": "What are YOU working on?",
            "cache": [],
            "cache_size": 200
        },
        "Programming-Help": {
            "description": "The helpful place",
            "cache": [],
            "cache_size": 200
        }
    }
    cache = []
    cache_size = 200

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        ChatSocketHandler.waiters.add(self)
        
        # Send the client all of the available rooms
        for room in ChatSocketHandler.rooms:
            self.write_message({"add_room": room })
		
		
		# Send all past messages to the user
        for msg in ChatSocketHandler.cache:
            try:
                self.write_message(msg)
            except:
                logging.error("Error sending message", exc_info=True)

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    @classmethod
    def send_updates(cls, chat):
        logging.info("sending message to %d waiters", len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error("Error sending message", exc_info=True)

    def on_message(self, message):
        logging.info("got message %r", message)
        parsed = tornado.escape.json_decode(message)
        chat = {
            "id": str(uuid.uuid4()),
            "body": parsed["body"],
			"user": "Test",
			"time": time.time(),
			"room": parsed["room"]
        }
		
		# Check that the room actually exists
        if ChatSocketHandler.rooms[parsed["room"]] == None:
            logging.error("The room " + parsed["room"] + " does not exist, ignoring message")
            return

        #chat["html"] = tornado.escape.to_basestring(
        #    self.render_string("message.html", message=chat))
        chat["html"] = tornado.escape.linkify(parsed["body"]);
        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
