#!/bin/python
# -*- coding: utf-8 -*-
# vim:set ts=8 sts=8 sw=8 tw=80 noet cc=80:

import sys
import configparser
import logging
import readline
from client import Client

import datetime

_TIME_FORMAT = '%Y%m%dT%H:%M:%S'

def time(at=None):
	"""Stringify time in ISO 8601 format."""
	if not at:
		at = utcnow()
	if type(at) == float:
		at = datetime.datetime.fromtimestamp(at)
	st = at.strftime(_TIME_FORMAT)
	tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
	st += ('Z' if tz == 'UTC' else tz)
	return st

def utcnow():
	return datetime.datetime.utcnow()

logger = logging.getLogger(__name__)

PROMPT = '%s%s '
mode = '>'
enable_bell = False

PLAIN = '>'
STEALTH = '$'
GOLD = '#'

xmpp = None

def prompt():
	global xmpp
	return PROMPT % (xmpp.nick, mode)

# clear current line, output text, show input line again
# FIXME: strip escape sequences from msg
def show(msg):
	line = readline.get_line_buffer()
	sys.stdout.write("\r\033[K%s\r\n%s%s" % (msg, prompt(), line))
	sys.stdout.flush()

class Help(object):
	def __init__(self, usage=None, info=None, see=[], topic=None):
		self.iscommand = usage is not None
		self.usage = usage
		self.info = info
		self.see = []

online_help = { "/help": Help("/help [command]", "shows help"),
		"/quit": Help("/quit", "quit the client"),
		"/encrypt": Help("/encrypt", "switch to encrypted (gold) mode. "
				"Everyone will see, that there was a message, "
				"but only users with the key can read them",
				see=["/plain", "/stealth", "/status"]),
		"/plain": Help("/plain", "switch to plaintext mode. This is the"
				" mode, every XMPP client supports.",
				see=["/encrypt", "/stealth", "/status"]),
		"/gold": Help("/gold", "alias for /encrypt", see=["/encrypt",
				"/stealth", "/status"]),
		"/stealth": Help("/stealth", "switch to stealth mode. Messages "
				"are sent encrypted and regular XMPP clients "
				"will not see the message at all",
				see=["/encrypt", "/plain", "/status"]),
		"/status": Help("/status", "show the current status.",
				see=["/encrypt", "/plain", "/stealth"]),
		"/msg": Help("/msg nick message", "send a private message to "
				"\"nick\"."),
		"/enc": Help("/enc text", "encrypt text and display the result "
				"locally. Probably only useful for debugging.",
				see=["/dec", "/encr"]),
		"/dec": Help("/dec text", "decrypt text and display the result "
				"locally. Probably only useful for debugging.",
				see=["/enc", "/encr"]),
		"/encr": Help("/encr text", "encrypt text in the same way as "
				"/enc does, but send the result unencrypted "
				"over XMPP. Probably only useful to annoy "
				"someone.", see=["/enc", "/dec"]),
		"/e": Help("/e text", "send encrypted text, exactly in the same"
				"way as in the \"encrypt\" mode, but without "
				"switching the mode.", see=["/encrypt"]),
		"/p": Help("/p text", "send plain text, exactly in the same "
				"way as in the \"plain\" mode, but without "
				"switching the mode.", see=["/plain"]),
		"/q": Help("/q text", "send text quietly (stealth), exactly in "
				"the same way as in the \"stealth\" mode, but "
				"without switching the mode.",
				see=["/stealth"]),
		"/say": Help("/say text", "send text literally. This allows to "
				"start a message with a \"/\"."),
		"/me": Help("/me text", "send a message starting with \"/me\". "
				"You know, why this might be useful..."),
		"/bell": Help("/bell [on|off]", "sets or shows the usage of the"
				" terminal's bell. If enabled, the bell will "
				"ring if a message is received."),
		"modes": Help(topic="Modes", info="There exist 3 different "
				"modes of operation: plaintext, encrypted and "
				"stealth mode. They influence how messages are "
				"sent and if a regular client can see and/or "
				"read them. The current mode is indicated by "
				"the last character of the prompt.\n"
				"> = plaintext, # = encrypted, $ = stealth",
				see=["/plain", "/encrypt", "/stealth",
					"/status"]),
		"about": Help(topic="About", info="This client was written to "
				"allow private group chats in public muc "
				"rooms. The encrypted mode was invented to "
				"show other participants, that a conversation "
				"is going on, and to show them, that they "
				"have no chance to participate. The stealth "
				"mode was invented to hide the fact, that there"
				" is a conversation at all. To make this "
				"possible, the XMPP protocol was extended, "
				"such that regular clients silently ignore the "
				"stealth messages, but the conference server "
				"still distributes them to all clients.")
		}

def print_help():
	print("commands: /help /quit /encrypt /plain /stealth /gold /status " \
			"/msg /enc /dec /e /encr /q /p /say /me /bell")

def show_help(subject):
	if subject in online_help:
		hlp = online_help[subject]
		if hlp.iscommand:
			text = "COMMAND: %s\nINFO: %s" % (hlp.usage, hlp.info)
		else:
			text = "INFO: %s" % hlp.info
		if len(hlp.see) > 0:
			text += "\nSEE: %s" % ", ".join(hlp.see)
		print(text)
	else:
		print("no help entry found")

xmpp = None
if __name__ == "__main__":
	logging.basicConfig(level=logging.ERROR,
		                        format="%(levelname)-8s %(message)s")

	filename = "xmpp.cfg"
	config = configparser.SafeConfigParser()
	config.read(filename)
	jid = config.get("xmpp", "jid")
	try:
		password = config.get("xmpp", "password")
	except:
		import getpass
		password = getpass.getpass("Password: ")
	room = config.get("xmpp", "room")
	nick = config.get("xmpp", "nick")
	key = config.get("xmpp", "key", fallback=None)
	logfile_name = config.get("client", "logfile", fallback="xmpp.log")
	enable_bell = config.getboolean("client", "bell", fallback=False)

	mode = GOLD if key is not None else PLAIN

	xmpp = Client(jid, password, room, nick, key)
	xmpp.register_plugin("xep_0030") # Service Discovery
	xmpp.register_plugin("xep_0045") # Multi-User Chat
	xmpp.register_plugin("xep_0199") # XMPP Ping
	xmpp.register_plugin("encrypt-im") # encrypted stealth MUC

	logfile = open(logfile_name, "a")

	def log_msg(msgtype, msg, nick):
		t = time()
		lines = msg.count("\n")
		line = "%sR %s %03d <%s> %s" % (msgtype, t, lines, nick, msg)
		try:
			logfile.write("%s\n" % line)
			logfile.flush()
		except Exception as e:
			show("exception while writing log: %s" % e)

	def log_status(info):
		t = time()
		lines = info.count("\n")
		line = "MI %s %03d %s" % (t, lines, info)
		try:
			logfile.write("%s\n" % line)
			logfile.flush()
		except Exception as e:
			show("exception while writing log: %s" % e)

	def muc_msg(msg, nick, jid, role, affiliation, stealth):
		if enable_bell:
			sys.stdout.write("\007")
		if stealth:
			if msg.startswith("/me "):
				show("$ *** %s %s" % (nick, msg[4:]))
			else:
				show("$ <%s> %s" % (nick, msg))
			log_msg("Q", msg, nick)
		else:
			if msg.startswith("/me "):
				show("*** %s %s" % (nick, msg[4:]))
			else:
				show("<%s> %s" % (nick, msg))
			log_msg("M", msg, nick)

	def muc_mention(msg, nick, jid, role, affiliation, stealth):
		if enable_bell:
			sys.stdout.write("\007")
		if stealth:
			show("$ <<<%s>>> %s" % (nick, msg))
			log_msg("Q", "%s: %s" % (xmpp.nick, msg), nick)
		else:
			show("<<<%s>>> %s" % (nick, msg))
			log_msg("M", "%s: %s" % (xmpp.nick, msg), nick)

	def priv_msg(msg, jid):
		if enable_bell:
			sys.stdout.write("\007")
		show("<PRIV#%s> %s" % (jid, msg))

	def muc_online(jid, nick, role, affiliation, localjid):
		show("*** online: %s (%s; %s)" % (nick, jid, role))
		log_status("%s <%s> has joined" % (nick, jid))

	def muc_offline(jid, nick):
		show("*** offline: %s" % nick)
		log_status("%s has left" % nick)

	def muc_joined():
		log_status('You have joined as "%s"' % xmpp.nick)

	xmpp.add_message_listener(muc_msg)
	xmpp.add_mention_listener(muc_mention)
	xmpp.add_online_listener(muc_online)
	xmpp.add_offline_listener(muc_offline)
	xmpp.add_private_listener(priv_msg)
	xmpp.add_init_complete_listener(muc_joined)

	if xmpp.connect():
		xmpp.process(block=False)
	else:
		print("Unable to connect")
		sys.exit(1)

	readline.read_init_file()
	try:
		while True:
			line = input(prompt())
			if not line:
				continue
			msg = line.strip()
			if len(msg) == 0:
				continue
			if msg == "/help":
				print_help()
			elif msg.startswith("/help "):
				text = msg[6:].strip()
				show_help(text)
			elif msg == "/quit":
				break
			elif msg == "/encrypt" or msg == "/gold":
				if xmpp.key is None:
					print("no encryption key set")
				else:
					xmpp.encrypt = True
					mode = GOLD
			elif msg == "/plain":
				xmpp.encrypt = False
				mode = PLAIN
			elif msg == "/stealth":
				if xmpp.key is None:
					print("no encryption key set")
				else:
					mode = STEALTH
			elif msg == "/status":
				print("key %s, mode is %s" % ("available" if
						xmpp.key is not None else
						"not available", "plaintext" if
						mode == PLAIN else "gold" if
						mode == GOLD else "stealth" if
						mode == STEALTH else "strange"))
			elif msg.startswith("/msg "):
				nick, text = None, None
				try:
					nick = msg[5:msg[5:].index(" ") + 5] \
							.strip()
					text = msg[5 + len(nick) + 1:].strip()
				except ValueError as e:
					print("syntax error")
				if nick is not None:
					xmpp.msg_send(nick, text, True)
			elif msg.startswith("/enc "):
				text = msg[5:].strip()
				if xmpp.key is None:
					print("error: no key set")
				else:
					try:
						data = xmpp.encode(text)
						print(data)
					except Exception as e:
						print("exception: %s" % e)
			elif msg.startswith("/dec "):
				text = msg[5:].strip()
				if xmpp.key is None:
					print("error: no key set")
				else:
					try:
						data = xmpp.decode(text)
						print("'%s'" % data)
					except Exception as e:
						print("exception: %s" % e)
			elif msg.startswith("/e "):
				text = msg[3:].strip()
				if xmpp.key is None:
					print("error: no key set")
				else:
					try:
						xmpp.muc_send(text, enc=True)
						log_msg("M", text, xmpp.nick)
					except Exception as e:
						print("exception: %s" % e)
			elif msg.startswith("/q "):
				text = msg[3:].strip()
				if xmpp.key is None:
					print("error: no key set")
				else:
					try:
						xmpp.muc_send(text,
								stealth=True)
						log_msg("Q", text, xmpp.nick)
					except Exception as e:
						print("exception: %s" % e)
			elif msg.startswith("/p "):
				text = msg[3:].strip()
				xmpp.muc_send(text, enc=False)
				log_msg("M", text, xmpp.nick)
			elif msg.startswith("/encr "):
				text = msg[6:].strip()
				if xmpp.key is None:
					print("error: no key set")
				else:
					try:
						data = xmpp.encode(text)
						xmpp.muc_send(data, enc=False)
						print("%s> %s" % (nick, data))
						log_msg("M", data, xmpp.nick)
					except Exception as e:
						print("exception: %s" % e)
			elif msg.startswith("/say "):
				text = msg[5:].strip()
				xmpp.muc_send(text)
				log_msg("Q" if mode == STEALTH else "M", msg,
						xmpp.nick)
			elif msg == "/bell":
				print("bell is %s" % ("enabled" if enable_bell
					else "disabled"))
			elif msg.startswith("/bell "):
				text = msg[6:].strip()
				if text == "on":
					enable_bell = True
					print("bell is now enabled")
				elif text == "off":
					enable_bell = False
					print("bell is now disabled")
				else:
					print("syntax error")
			elif msg[0] == "/" and not msg.startswith("/me "):
				print("unknown command")
			else:
				if mode == STEALTH:
					xmpp.muc_send(msg, stealth=True)
					log_msg("Q", msg, xmpp.nick)
				else:
					xmpp.muc_send(msg)
					log_msg("Q" if mode == STEALTH else "M",
							msg, xmpp.nick)

	except KeyboardInterrupt: pass
	except EOFError: pass

	xmpp.disconnect()
