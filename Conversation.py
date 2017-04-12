# -*- coding: utf-8 -*-

from WordMarkovChain import WordMarkovChain
import operator
import random

class Conversation:

    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.chain = WordMarkovChain()
        self.reverse_chain = WordMarkovChain()
        self.someones = set()

    def add_message(self, message):
        message = message.lower().split()
        self.chain.add_message(message)
        message.reverse()
        self.reverse_chain.add_message(message)

    def add_someone(self, someone):
        self.someones.add(someone)

    def is_there_someone(self,):
        return len(self.someones) > 0

    def get_someone(self, quantity):
        return random.sample(self.someones,quantity)
        
    def get_someone(self):
        if len(self.someones) > 0:
            return random.sample(self.someones, 1)[0]

    def get_someones(self):
        return ", ".join(self.someones)

    def generate_message(self):
        return self.chain.build_message()

    def generate_message_beginning_with(self, words):
        if len(words) > 0:
            generated_message = self.chain.build_message(words[-1]).split()
            return " ".join(words + generated_message[1:]).lower()

    def generate_message_ending_with(self, words):
        if len(words) > 0:
            generated_message = self.reverse_chain.build_message(words[0]).split()
            generated_message.reverse()
            return " ".join(generated_message[:-1] + words).lower()

    def generate_message_containing(self, words):
        if len(words) > 0:
            message_beginning = self.reverse_chain.build_message(words[0]).split()
            message_beginning.reverse()
            message_end = self.chain.build_message(words[-1]).split()
            return " ".join(message_beginning[:-1] + words + message_end[1:]).lower()

    def print_chain(self, word, reverse=False):
        arg = word.lower()
        if not reverse:
            probabilities = self.chain.probabilities_for(arg)
            printed_chain = "Probabilities to appear after '" + arg + "':"
            message_extreme = "End of message"
        else:
            probabilities = self.reverse_chain.probabilities_for(arg)
            printed_chain = "Probabilities to appear before '" + arg + "':"
            message_extreme = "Beginning of message"

        if probabilities:
            for word, prob in reversed(sorted(probabilities.items(), key=operator.itemgetter(1))):
                if word:
                    printed_chain += "\n - '" + word.decode("utf-8") + "': " + unicode(prob)
                else:
                    printed_chain += "\n - " + message_extreme + ": " + unicode(prob)
        else:
            printed_chain = "The word '" + arg + "' doesn't seem to be in my database"

        return printed_chain

    def set_randomness(self, p):
        if 0 <= p <= 1:
            self.chain.set_randomness(p)
            self.reverse_chain.set_randomness(p)
        else:
            raise (ValueError, "Randomness should be a number between 0 and 1")

    def import_chain(self, filename):
        self.chain.import_chain(filename)
        self.reverse_chain.import_chain(filename, reverse=True)

    def export_chain(self, filename):
        self.chain.export_chain(filename)
