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
            print message
        if self.log_to_file:
            f = open(self.filename, 'a')
            f.write(message.encode("utf-8") + "\n")
            f.close()


class MarcosBot:
    public_commands = ["message", "beginwith", "endwith", "use", "chain", "reversechain"]
    private_commands = ["setrandomness", "removeword", "removetransition", "backup"]

    def __init__(self, token, special_users, log_file=None, easter_eggs={}):
        self.token = token
        self.special_users = special_users
        self.bot = telepot.Bot(token)
        self.conversations = dict()
        self.log = Log(filename=log_file)
        self.log.log("Hello!")
        self.easter_eggs = easter_eggs
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
            self.log.log("Error: unrecognized message type", message["chat"]["id"], get_full_name(message))
            return

        conversation = self._add_conversation(chat_id)

        if content_type == "text":
            text = message["text"]
            spl_text = text.split()

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
                            self.log.log("Error (unauthorized attempt to execute /" + unicode(command) + ")", chat_id, get_full_name(message))
                        return

            conversation.add_message(text)
            self.log.log("Recieved: " + text, chat_id, get_full_name(message))

    def handle_message(self, message, conversation, args):
        generated_message = conversation.generate_message()
        if not generated_message:
            generated_message = "My database seems to be empty!"
        self.bot.sendMessage(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
        self.log.log("Generated: " + generated_message, conversation.chat_id, get_full_name(message))

    def handle_beginwith(self, message, conversation, args):
        if len(args) > 0:
            generated_message = conversation.generate_message_beginning_with(args)
            self.bot.sendMessage(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
            self.log.log("Generated (/beginwith " + " ".join(args) + "): " + generated_message, conversation.chat_id, get_full_name(message))
        else:
            self.log.log("Error (empty /beginwith)", conversation.chat_id, get_full_name(message))

    def handle_endwith(self, message, conversation, args):
        if len(args) > 0:
            generated_message = conversation.generate_message_ending_with(args)
            self.bot.sendMessage(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
            self.log.log("Generated (/endwith " + " ".join(args) + "): " + generated_message, conversation.chat_id, get_full_name(message))
        else:
            self.log.log("Error (empty /endwith)", conversation.chat_id, get_full_name(message))

    def handle_use(self, message, conversation, args):
        if len(args) > 0:
            generated_message = conversation.generate_message_containing(args)
            self.bot.sendMessage(conversation.chat_id, self._apply_easter_eggs(generated_message, conversation.chat_id))
            self.log.log("Generated (/use " + " ".join(args) + "): " + generated_message, conversation.chat_id, get_full_name(message))
        else:
            self.log.log("Error (empty /use)", conversation.chat_id, get_full_name(message))

    def handle_chain(self, message, conversation, args):
        if len(args) > 0:
            chain = conversation.print_chain(args[0])
            self.bot.sendMessage(conversation.chat_id, chain, reply_to_message_id =message["message_id"])
            self.log.log("Printed chain for '" + args[0] + "'", conversation.chat_id, get_full_name(message))
        else:
            self.log.log("Error (empty /chain)", conversation.chat_id, get_full_name(message))

    def handle_reversechain(self, message, conversation, args):
        if len(args) > 0:
            chain = conversation.print_chain(args[0], reverse=True)
            self.bot.sendMessage(conversation.chat_id, chain, reply_to_message_id =message["message_id"])
            self.log.log("Printed reverse chain for '" + args[0] + "'", conversation.chat_id, get_full_name(message))
        else:
            self.log.log("Error (empty /reversechain)", conversation.chat_id, get_full_name(message))

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


parser = argparse.ArgumentParser(description='Hello, I am the Marcos Bot.')
parser.add_argument('-d', metavar="data_dir", type=str, dest='data_dir',
                    help='directory from where to load and store data')
parser.add_argument('-l', metavar="log_file", type=str, dest='log_file',
                    help='file where to save logging information')
parser.add_argument('-f', dest='finish', action='store_true',
                   help='don\'t keep the program running forever')

program_args = parser.parse_args()


with open("config.json") as config_file:
    config = json.load(config_file)


token = config["token"]

special_users = [int(user) for user in config["special_users"]]

easter_eggs = dict()
for conv in config["easter_eggs"]:
    easter_eggs[int(conv)] = config["easter_eggs"][conv]

log_file = program_args.log_file if program_args.log_file else None


bot = MarcosBot(token, special_users, log_file=log_file, easter_eggs=easter_eggs)

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
