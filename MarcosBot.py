# -*- coding: utf-8 -*-

from Conversation import Conversation
import telepot
from datetime import datetime
import time
import os
import argparse
import signal
import random
import json


# Replace ascii with utf-8 encoding
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


def get_full_name(message):
    username = ""
    if "first_name" in message["from"]:
        username += message["from"]["first_name"]
    if "first_name" in message["from"] and "last_name" in message["from"]:
        username += " "
    if "last_name" in message["from"]:
        username += message["from"]["last_name"]

    return username


class Log:
    def __init__(self, filename = None, log_to_stdout = True):
        self.log_to_stdout = log_to_stdout
        if type(filename) in [str, unicode]:
            self.log_to_file = True
            self.filename = filename
        else:
            self.log_to_file = False

    def log(self, text, chat_id=None, username=None, private=False):
        now = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        message = "[" + now + "] "
        if chat_id:
            message += "<" + unicode(chat_id) + "> "
        if username:
            if private:
                message += "{" + unicode(username) + "} "
            else:
                message += "(" + unicode(username) + ") "
        message += unicode(text)

        if self.log_to_stdout:
            print message.encode("utf-8")
        if self.log_to_file:
            f = open(self.filename, 'a')
            f.write(message.encode("utf-8") + "\n")
            f.close()

    def log_m(self, text, message):
        self.log(text, message["chat"]["id"], get_full_name(message), message["chat"]["type"] == "private")


class MarcosBot:
    public_commands = ["start", "message", "beginwith", "endwith", "use", "chain", "reversechain", "someone", "people"]
    private_commands = ["setrandomness", "backup"]

    def __init__(self, token, special_users, log_file=None, easter_eggs={}, conv_overrides={}, log_to_stdout=True):
        self.token = token
        self.special_users = special_users
        self.bot = telepot.Bot(token)
        self.conversations = dict()
        self.log = Log(filename=log_file, log_to_stdout=log_to_stdout)
        self.log.log("Hello!")
        self.easter_eggs = easter_eggs
        self.conv_overrides = conv_overrides
        self.username = self.bot.getMe()["username"]

    def __del__(self):
        self.log.log("Goodbye!")

    def listen(self):
        self.bot.message_loop(self.handle)
        self.log.log("Listening...")

    def handle(self, message):
        try:
            content_type, chat_type, chat_id = telepot.glance(message)
        except KeyError:
            self.log.log_m("Error: unrecognized message type", message)
            return

        if chat_id in self.conv_overrides:
            eff_chat_id = self.conv_overrides[chat_id]
        else:
            eff_chat_id = chat_id

        conversation = self._add_conversation(eff_chat_id)

        if content_type == "text":
            text = message["text"]
            spl_text = text.split()

            self.log.log_m("Recieved: " + text, message)

            self.handle_ayylmao(text, conversation)

            if len(spl_text) > 0 and spl_text[0][0] == "/":
                command = spl_text[0][1:].split("@")
                if len(command) < 2 or command[1] == self.username:
                    command = command[0]
                    args = spl_text[1:]
                    if command in self.public_commands:
                        handler = getattr(self, "handle_" + command)
                        handler(message, conversation, args)
                        return
                    elif command in self.private_commands:
                        if message["from"]["id"] in special_users:
                            handler = getattr(self, "handle_" + command)
                            handler(message, conversation, args)
                        else:
                            self.log.log_m("Error (unauthorized attempt to execute /" + unicode(command) + ")", message)
                        return

            conversation.add_message(text)
            self.log.log_m("Added: " + text, message)
            conversation.add_someone(get_full_name(message))

        else:
            self.log.log_m("Ignored non-text message (content type: " + content_type + ")", message)

    def handle_start(self, message, conversation, args):
        self._send_fragmented(conversation.chat_id, "Hello! I am Marcos the Bot. Talk to me and I will generate random messages based on the things you say.")
        self.log.log_m("Greeting sent", message)

    def handle_message(self, message, conversation, args):
        generated_message = conversation.generate_message()
        if not generated_message:
            generated_message = "My database seems to be empty! Say something before"
        self._send_fragmented(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
        self.log.log_m("Generated: " + generated_message, message)

    def handle_beginwith(self, message, conversation, args):
        if conversation.is_there_someone():
            args = self._replace_people(conversation, args)
        if len(args) > 0:
            generated_message = conversation.generate_message_beginning_with(args)
            self._send_fragmented(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
            self.log.log_m("Generated (/beginwith " + " ".join(args) + "): " + generated_message, message)
        else:
            self.log.log_m("Error (empty /beginwith)", message)
            self._send_fragmented(conversation.chat_id, "An argument seems to be missing!")

    def handle_endwith(self, message, conversation, args):
        if conversation.is_there_someone():
            args = self._replace_people(conversation, args)
        if len(args) > 0:
            generated_message = conversation.generate_message_ending_with(args)
            self._send_fragmented(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
            self.log.log_m("Generated (/endwith " + " ".join(args) + "): " + generated_message, message)
        else:
            self.log.log_m("Error (empty /endwith)", message)
            self._send_fragmented(conversation.chat_id, "An argument seems to be missing!")

    def handle_use(self, message, conversation, args):
        if conversation.is_there_someone():
            args = self._replace_people(conversation, args)
        if len(args) > 0:
            generated_message = conversation.generate_message_containing(args)
            self._send_fragmented(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
            self.log.log_m("Generated (/use " + " ".join(args) + "): " + generated_message, message)
        else:
            self.log.log_m("Error (empty /use)", message)
            self._send_fragmented(conversation.chat_id, "An argument seems to be missing!")

    def handle_chain(self, message, conversation, args):
        if len(args) > 0:
            chain = conversation.print_chain(args[0])
            self._send_fragmented(conversation.chat_id, chain, reply_to_message_id =message["message_id"])
            self.log.log_m("Printed chain for '" + args[0] + "'", message)
        else:
            self.log.log_m("Error (empty /chain)", message)
            self._send_fragmented(conversation.chat_id, "An argument seems to be missing!")

    def handle_reversechain(self, message, conversation, args):
        if len(args) > 0:
            chain = conversation.print_chain(args[0], reverse=True)
            self._send_fragmented(conversation.chat_id, chain, reply_to_message_id =message["message_id"])
            self.log.log_m("Printed reverse chain for '" + args[0] + "'", message)
        else:
            self.log.log_m("Error (empty /reversechain)", message)
            self._send_fragmented(conversation.chat_id, "An argument seems to be missing!")

    def handle_setrandomness(self, message, conversation, args):
        if len(args) > 0:
            p = float(args[0])
            if 0 <= p <= 1:
                conversation.set_randomness(p)
                self._send_fragmented(conversation.chat_id, "Randomness set to " + str(p), reply_to_message_id=message["message_id"])
                self.log.log_m("Randomness set to " + str(p), message)
            else:
                self._send_fragmented(conversation.chat_id, "Randomness should be a number between 0 and 1!", reply_to_message_id=message["message_id"])
                self.log.log_m("Error (invalid parameter for /setrandomness)", message)
        else:
            self.log.log_m("Error (empty /setrandomness)", message)
            self._send_fragmented(conversation.chat_id, "An argument seems to be missing!")

    def handle_ayylmao(self, text, conversation):
        import re

        match = re.search('rip', text, flags=re.IGNORECASE)
        if match:
            self._send_fragmented(conversation.chat_id, "in pieces")

        match = re.search('alien|ayy.*lmao|lmao.*ayy', text, flags=re.IGNORECASE)
        if match:
            self._send_fragmented(conversation.chat_id, "ayy lmao")
        else:
            match = re.search('ayy(y*)', text, flags=re.IGNORECASE)
            if match:
                count = len(match.group(1))
                self._send_fragmented(conversation.chat_id, "lmao" + "".join(["o" for i in range(count)]))

            match = re.search('lmao(o*)', text, flags=re.IGNORECASE)
            if match:
                count = len(match.group(1))
                self._send_fragmented(conversation.chat_id, "ayy" + "".join(["y" for i in range(count)]))

    def handle_someone(self, message, conversation, args):
        if not conversation.is_there_someone():
            generated_message = "No one has spoken yet!"
        else:
            generated_message = " ".join(self._replace_people(conversation, args)).lower()
        self._send_fragmented(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
        self.log.log_m("Generated (/someone): " + generated_message, message)

    def handle_people(self, message, conversation, args):
        generated_message = conversation.get_someones()
        if generated_message == "":
            generated_message = "No one has spoken yet!"
        self._send_fragmented(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
        self.log.log_m("Printed list of people: " + generated_message, message)

    def import_chain(self, chat_id, filename):
        chat_id = int(chat_id)
        conversation = self._add_conversation(chat_id)
        self.log.log("Importing chain for chat id " + unicode(chat_id) + " from '" + unicode(filename) + "'")
        conversation.import_chain(filename)

    def export_chain(self, chat_id, filename):
        chat_id = int(chat_id)
        if chat_id in self.conversations:
            conversation = self.conversations[chat_id]
            conversation.export_chain(filename)
            self.log.log("Exporting chain for chat id " + unicode(chat_id) + " to '" + unicode(filename) + "'")
        else:
            self.log.log("Error: exporting chain for chat id " + unicode(chat_id) + " (chat does not exist)")

    def export_all_chains(self, directory):
        self.log.log("Exporting all data...")
        for chat_id in self.conversations:
            self.conversations[chat_id].export_chain(directory + "/" + str(chat_id))
            self.log.log("Exporting chain for chat id " + unicode(chat_id) + " to '" + unicode(directory) + "/" + unicode(chat_id) + "'")

    def _add_conversation(self, chat_id):
        if chat_id in self.conversations:
            conversation = self.conversations[chat_id]
        else:
            conversation = Conversation(chat_id)
            self.conversations[chat_id] = conversation
            self.log.log("Adding conversation " + unicode(chat_id))
        return conversation

    def _apply_easter_eggs(self, message, chat_id):
        if chat_id in self.easter_eggs:
            if "follow_with" in self.easter_eggs[chat_id]:
                follow_with = self.easter_eggs[chat_id]["follow_with"]
                message = message.split()
                for i in range(len(message)):
                    if message[i] in follow_with:
                        accum = 0
                        for egg in follow_with[message[i]]:
                            chance = follow_with[message[i]][egg]
                            if random.uniform(0, 1 - accum) < chance:
                                message[i] += " " + egg.decode("utf-8")
                                break
                message = " ".join(message)
        return message

    def _replace_people(self, conversation, message):
        generated_message = []
        symbols = {}
        for word in message:
            if word[0] == "@":
                symbols[word] = None

        if len(symbols) > len(conversation.someones):
            return "No enough someones".split()

        generated_names = conversation.get_someone(len(symbols))

        i = 0
        for k,v in symbols.iteritems():
            v = generated_names[i]
            i += 1

        for word in message:
            if word[0] == "@":
                generated_message.append(symbols[word])
            else:
                generated_message.append(word)

        return generated_message

    def _send_fragmented(self, chat_id, message, **kwargs):
        while len(message) > 2048:
            fragment = message[0:2042] + " [...]"
            self.bot.sendMessage(chat_id, fragment, **kwargs)
            message = "[...] " + message[2042:]
        if len(message) > 0:
            self.bot.sendMessage(chat_id, message, **kwargs)

parser = argparse.ArgumentParser(description='Hello, I am the Marcos Bot.')
parser.add_argument('-d', metavar="data_dir", type=str, dest='data_dir',
                    help='directory from where to load and store data')
parser.add_argument('-l', metavar="log_file", type=str, dest='log_file',
                    help='file where to save logging information')
parser.add_argument('-f', dest='finish', action='store_true',
                   help='don\'t keep the program running forever')
parser.add_argument('-v', dest='log_to_stdout', action='store_true',
                    help='print debugging information to standard output')

program_args = parser.parse_args()


with open("config.json") as config_file:
    config = json.load(config_file)


token = config["token"]

special_users = [int(user) for user in config["special_users"]]

easter_eggs = dict()
for conv in config["easter_eggs"]:
    easter_eggs[int(conv)] = config["easter_eggs"][conv]

conv_overrides = dict()
for conv in config["conv_overrides"]:
    conv_overrides[int(conv)] = int(config["conv_overrides"][conv])

log_file = program_args.log_file if program_args.log_file else None
log_to_stdout = program_args.log_to_stdout


bot = MarcosBot(token, special_users, log_file=log_file, easter_eggs=easter_eggs, conv_overrides=conv_overrides, log_to_stdout=log_to_stdout)

if program_args.data_dir:
    for filename in os.listdir(program_args.data_dir):
         bot.import_chain(filename, program_args.data_dir + "/" + filename)

def save_and_exit(signal, frame):
    if program_args.data_dir:
        bot.export_all_chains(program_args.data_dir)
    sys.exit(0)

signal.signal(signal.SIGINT, save_and_exit)
signal.signal(signal.SIGTERM, save_and_exit)

bot.listen()

if not program_args.finish:
    while True:
        time.sleep(10)
