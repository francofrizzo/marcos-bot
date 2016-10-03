#!/usr/bin/env python
# -*- coding: utf-8 -*-

from WordMarkovChain import WordMarkovChain

import telebot
import random
import re
import time
import datetime
import argparse
import pickle
import traceback
import random

# Replace ascii with unicode encoding
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


# Auxiliary functions
def print_username(message):
    username = ""
    if message.from_user.first_name:
        username += message.from_user.first_name
    if message.from_user.first_name and message.from_user.last_name:
        username += " "
    if message.from_user.last_name:
        username += message.from_user.last_name

    chat_is_private = message.chat.type == "private"

    return ("{" if chat_is_private else "(") + username + ("}" if chat_is_private else ")")

def current_datetime():
    return datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")

def log(message_content):
    message = "[" + current_datetime() + "] " + str(message_content)

    f = open('logs/marcos.log', 'a')
    f.write(message + "\n")
    f.close()

    print message

def load_chain_legacy(filename):
    with open(filename + '_count.pkl', 'rb') as f:
        chain_count = pickle.load(f)

    chain = WordMarkovChain()

    for word1 in chain_count:
        for word2 in chain_count[word1]:
            for i in range(chain_count[word1][word2]):
                if word1 == 0:
                    chain.add_occurrence_at_start(word2)
                elif word2 == 1:
                    chain.add_occurrence_at_end(word1)
                else:
                    chain.add_transition_between(word1, word2)

    return chain

# IDs of users with special permissions
special_users = [144412810]


# Parsing arguments
parser = argparse.ArgumentParser(description='Hello, I am the Marcos Bot.')
parser.add_argument('-f', metavar="file", type=str, dest='file',
                   help='file from where to load data')
parser.add_argument('--legacy', dest='legacy', action='store_true',
                   help='read file in legacy mode')

args = parser.parse_args()


# Initializing
bot = telebot.TeleBot("298046017:AAFhBT_YwGxKwq6FMV-PQP9BXtkeDNqf2Fs")
chain = WordMarkovChain()
reverse_chain = WordMarkovChain()

if args.file:
    if args.legacy:
        chain = load_chain_legacy(args.file)
    else:
        chain.import_chain(args.file)
        reverse_chain.import_chain(args.file, True)

# Public commands
@bot.message_handler(commands=['message'])
def bot_send_message(message):
    generated_message = chain.build_message()
    if not generated_message:
        generated_message = "My database seems to be empty!"
    bot.send_message(message.chat.id, generated_message)
    log("[G] " + print_username(message) + ": " + generated_message)

@bot.message_handler(commands=['beginwith'])
def bot_begin_with(message):
    message_content = message.text.split()
    if len(message_content) > 1:
        message_content.pop(0)
        start = message_content.pop().lower()
        if start in ["ladrón", "chanta", "chorro"]:   # Easter egg
            start = "walter"
        if len(message_content) > 0:
            message_content = (" ".join(message_content)) + " "
        else:
            message_content = ""
        generated_message = message_content + chain.build_message(start)
        if generated_message:
            bot.send_message(message.chat.id, generated_message)
        log("[B] " + print_username(message) + ": " + generated_message)
    else:
        log("[E] " + print_username(message) + ": Error (empty /beginwith)")

@bot.message_handler(commands=['endwith'])
def bot_end_with(message):
    message_content = message.text.split()
    message_content.reverse()
    if len(message_content) > 1:
        message_content.pop()
        end = message_content.pop().lower()
        if len(message_content) > 0:
            message_content.reverse()
            message_content = " " + (" ".join(message_content))
        else:
            message_content = ""
        generated_message = reverse_chain.build_message(end).split()
        length = len(generated_message)
        while length < 2 and random.random() < 0.9:
            generated_message = reverse_chain.build_message(end).split()
            length = len(generated_message)
        generated_message.reverse()
        generated_message = " ".join(generated_message) + message_content
        if generated_message:
            bot.send_message(message.chat.id, generated_message)
        log("[B] " + print_username(message) + ": " + generated_message)
    else:
        log("[E] " + print_username(message) + ": Error (empty /endwith)")

@bot.message_handler(commands=['printchain'])
def bot_print_chain(message):
    try:
        arg = message.text.split()[1].lower()
        probabilities = chain.probabilities_for(arg)
        if probabilities:
            generated_message = "Probabilities for '" + arg + "':"
            for word in probabilities:
                if word:
                    generated_message += "\n - '" + word + "': " + str(probabilities[word])
                else:
                    generated_message += "\n - End of message: " + str(probabilities[word])
        else:
            generated_message = "The word '" + arg + "' doesn't seem to be in my database"
        bot.reply_to(message, generated_message)
        log("[Printed chain for: " + arg +"] " + print_username(message))
    except IndexError:
        log("[E] " + print_username(message) + ": Error (/printchain)")


# # Private commands
@bot.message_handler(commands=['setrandomness'])
def bot_set_randomness(message):
    if message.from_user.id in special_users:
        try:
            p = float(message.text.split()[1])
            try:
                chain.set_randomness(p)
                bot.reply_to(message, "Randomness set to " + str(p))
                log("[Randomness set to " + str(p) + "] " + print_username(message))
            except ValueError:
                bot.reply_to(message, "Randomness must ve a value between 0 and 1")
                log("[Error: invalid randomness value] " + print_username(message))
        except:
            bot.reply_to(message, "An error occurred")
            log("[Error: /setrandomness] " + print_username(message))
    else:
        bot.reply_to(message, "Who do you think you are?!")
        log("[Unauthorized: /setrandomness] " + print_username(message))

@bot.message_handler(commands=['removeword'])
def bot_remove_word(message):
    if message.from_user.id in special_users:
        try:
            arg = message.text.split()[1].lower()
            chain.remove_word(arg)
            bot.reply_to(message, "Removed: " + arg)
            log("[Removed: " + arg + "] " + print_username(message))
        except IndexError:
            bot.reply_to(message, "An error occurred")
            log("[Error: /removeword] " + print_username(message))
    else:
        bot.reply_to(message, "Who do you think you are?!")
        log("[Unauthorized: /removeword] " + print_username(message))

@bot.message_handler(commands=['removetransition'])
def remove_transition(message):
    if message.from_user.id in special_users:
        try:
            arg1 = message.text.split()[1].lower()
            arg2 = message.text.split()[2].lower()
            chain.remove_transition(arg1, arg2)
            bot.reply_to(message, "Removed transition: " + arg1 + " -> " + arg2)
            log("[Removed transition: " + arg1 + " -> " + arg2 + "] " + print_username(message))
        except IndexError:
            bot.reply_to(message, "An error occurred")
            log("[Error: /removetransition] " + print_username(message))
    else:
        bot.reply_to(message, "Who do you think you are?!")
        log("[Unauthorized: /removetransition] " + print_username(message))

@bot.message_handler(commands=['backup'])
def backup_data(message):
    if message.from_user.id in special_users:
        chain.export_chain("marcos_chain.bkp")
        bot.reply_to(message, "Data was just backuped")
        log("[Data backuped] " + print_username(message))
    else:
        bot.reply_to(message, "Who do you think you are?!")
        log("[Unauthorized: /backup] " + print_username(message))


# Adding new messages (at the end so it capures everything else)
@bot.message_handler(func=lambda m: True)
def bot_add_message(message):
    chain.add_message(message.text)
    reversed_message = message.text.split()
    reversed_message.reverse()
    reverse_chain.add_message(" ".join(reversed_message))
    log("[R] " + print_username(message) + ": " + message.text)


# Let the magic happen!
retry = True
wait_for_retry = 0
while retry:
    retry = False
    try:
        last_try = datetime.datetime.now()
        bot.polling()
        chain.export_chain("marcos_chain")
        log("[Data saved]")
        log("[Goodbye!]")
    except Exception as e:
        if datetime.datetime.now() - last_try > datetime.timedelta(seconds=128):
            wait_for_retry = 0
        log("[An error occurred]")
        log(e)
        traceback.print_exc()
        chain.export_chain("marcos_chain.bkp")
        log("[Data backuped]")
        retry = True
        if wait_for_retry == 0:
            log("[Retrying...]")
            wait_for_retry = 1
        else:
            log("[Retrying in " + str(wait_for_retry) + " seconds...]")
            time.sleep(wait_for_retry)
            if wait_for_retry < 64:
                wait_for_retry = 2 * wait_for_retry