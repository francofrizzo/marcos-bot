# -*- coding: utf-8 -*-

import random
import gzip


class RandomCollection:

    def __init__(self):
        self.total = 0
        self.frequencies = {}

    def add_occurrence(self, item, count = 1):
        self.total += count
        if item in self.frequencies:
            self.frequencies[item] += count
        else:
            self.frequencies[item] = count

    def remove_occurrence(self, item, count = 1):
        if item in self.frequencies:
            if self.frequencies[item] > count:
                self.total -= count
                self.frequencies[item] -= count
            else:
                self.total -= self.frequencies[item]
                del self.frequencies[item]
            return True
        else:
            return False

    def remove_item(self, item):
        if item in self.frequencies:
            self.total -= self.frequencies[item]
            del self.frequencies[item]
            return True
        else:
            return False

    def choose_one(self):
        if self.total > 0:
            chosen = random.randrange(0, self.total)
            current = 0

            for item in self.frequencies:
                current += self.frequencies[item]
                if current > chosen:
                    return item

        else:
            return None

    def occurrences_of(self, item):
        if item in self.frequencies:
            return self.frequencies[item]
        else:
            return 0

    def total_occurrences(self):
        return self.total

    def probability_of(self, item):
        if item in self.frequencies:
            return float(self.frequencies[item]) / float(self.total)
        else:
            return float(0)

    def probabilities(self):
        ret = {}
        for item in self.frequencies:
            ret[item] = self.probability_of(item)
        return ret

    def __iter__(self):
        return self.frequencies.__iter__()


class Word:
    def __init__(self, string):
        self.string = string
        self.transitions = RandomCollection()

    def __str__(self):
        return self.string.__str__()

    def __unicode__(self):
        return self.string.decode("utf-8")

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.string == other.string
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented

    def __hash__(self):
        return hash(self.string)

    def __iter__(self):
        return self.transitions.__iter__()

    def add_transition_to(self, word, count = 1):
        self.transitions.add_occurrence(word, count)

    def remove_transition_to(self, word, count = 1):
        return self.transitions.remove_occurrence(word, count)

    def remove_link_to(self, word):
        return self.transitions.remove_item(word)

    def add_occurrence_at_end(self, count = 1):
        self.transitions.add_occurrence(False, count)

    def remove_occurrence_at_end(self, count = 1):
        return self.transitions.remove_occurrence(False, count)

    def remove_all_occurrences_at_end(self):
        return self.transitions.remove_item(False)

    def generate_next_word(self):
        return self.transitions.choose_one()

    def probabilities(self):
        return self.transitions.probabilities()

    def transitions_to(self, word):
        return self.transitions.occurrences_of(word)


class WordMarkovChain:
    def __init__(self):
        self.words = {}
        self.start_words = RandomCollection()
        self.randomness = 0.1

    def remove_word(self, string):
        if string in self.words:
            word = self.words[string]
            for other_word in self.words:
                self.words[other_word].remove_link_to(word)
            del self.words[string]
            return True
        else:
            return False

    def add_transition_between(self, string1, string2, count = 1):
        word1 = self._add_word(string1)
        word2 = self._add_word(string2)

        word1.add_transition_to(word2, count)

    def remove_transition_between(self, string1, string2, count = 1):
        word1 = self._get_word(string1)
        word2 = self._get_word(string2)

        if word1 and word2:
            return word1.remove_transition_to(word2, count)
        else:
            return False

    def add_occurrence_at_start(self, string, count = 1):
        word = self._add_word(string)
        self.start_words.add_occurrence(word, count)

    def remove_occurrence_at_start(self, string, count = 1):
        word = self._get_word(string)
        if word:
            return self.start_words.remove_occurrence(word, count)
        else:
            return False

    def add_occurrence_at_end(self, string, count = 1):
        word = self._add_word(string)
        word.add_occurrence_at_end(count)

    def remove_occurrence_at_end(self, string, count = 1):
        word = self._get_word(string)
        if type(word) == Word:
            return word.remove_occurrence_at_end(count)
        else:
            return False

    def add_message(self, strings):
        if len(strings) > 0:
            word1 = self._add_word(strings.pop(0))
            self.start_words.add_occurrence(word1)

            for string in strings:
                word2 = self._add_word(string)
                word1.add_transition_to(word2)
                word1 = word2

            word1.add_occurrence_at_end()

    def build_message(self, start = False):
        # This list will contain the words of the generated message
        message = []

        if start:
            # If a first word for the message was provided,
            # retrieves this first word and adds it to the message
            cur_word = self._get_word(start)
            if not cur_word:
                # If the word provided is not in the database, generate
                # a random one
                message.append(start)
                cur_word = self._generate_first_word()
            message.append(unicode(cur_word))
            # What follows enforces at least a second word in the message
            next_word = cur_word.generate_next_word()
            while not next_word:
                if random.random() < 0.05:
                    # This is to break infinite loops if the word has no
                    # non-empty successor
                    # (Could be improved by looking that up instead of
                    # relying in randomness)
                    next_word = self._generate_random_word()
                else:
                    next_word = cur_word.generate_next_word()
            cur_word = next_word
        else:
            # Generates a random first word for the message
            cur_word = self._generate_first_word()

        while cur_word:
            # While message end has not been reached, keeps adding a word
            # and generating a next one
            if random.random() < self.randomness:
                # With certain chance, generate a completely random word
                cur_word = self._generate_random_word()
            message.append(unicode(cur_word))
            cur_word = cur_word.generate_next_word()

        # Return the message as a space-joined string
        return " ".join(message)

    def set_randomness(self, p):
        if 0 <= p <= 1:
            self.randomness = p
        else:
            raise(ValueError, "Randomness should be a number between 0 and 1")

    def probabilities_for(self, string):
        word = self._get_word(string)
        if word:
            ret = {}
            probabilities = word.probabilities()
            for word in probabilities:
                if word:
                    ret[str(word)] = probabilities[word]
                else:
                    ret[word] = probabilities[word]
            return ret
        else:
            return False

    def export_chain(self, filename):
        # f = gzip.open(filename, 'w')
        f = open(filename, 'w')
        for word in self.start_words:
            occurrences = str(self.start_words.occurrences_of(word))
            line = ["-", "start", word.string, occurrences]
            f.write(" ".join(line) + "\n")
        for word1 in self.words:
            for word2 in self.words[word1]:
                occurrences = str(self.words[word1].transitions_to(word2))
                if word2:
                    line = [word1, word2.string, occurrences]
                else:
                    line = ["-", "end", word1, occurrences]
                f.write(" ".join(line) + "\n")
        f.close()

    def import_chain(self, filename, reverse = False):
        # f = gzip.open(filename, 'r')
        f = open(filename, 'r')
        for line in f:
            line = line.split()
            if len(line) == 4:
                if line[1] == "start":
                    if not reverse:
                        self.add_occurrence_at_start(line[2], int(line[3]))
                    else:
                        self.add_occurrence_at_end(line[2], int(line[3]))
                elif line[1] == "end":
                    if not reverse:
                        self.add_occurrence_at_end(line[2], int(line[3]))
                    else:
                        self.add_occurrence_at_start(line[2], int(line[3]))
            elif len(line) == 3:
                if not reverse:
                    self.add_transition_between(line[0], line[1], int(line[2]))
                else:
                    self.add_transition_between(line[1], line[0], int(line[2]))
        f.close()

    def _add_word(self, string):
        if string in self.words:
            return self.words[string]
        else:
            word = Word(string)
            self.words[string] = word
            return word

    def _get_word(self, string):
        if string in self.words:
            return self.words[string]
        else:
            return False

    def _generate_first_word(self):
        return self.start_words.choose_one()

    def _generate_random_word(self):
        if self.words:
            chosen = random.choice(self.words.keys())
            return self.words[chosen]
        else:
            return False

