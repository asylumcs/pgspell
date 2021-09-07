#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
  pgspell.py
  MIT license (c) 2021 Asylum Computer Services LLC
  https://asylumcs.net
"""

# pylint: disable=C0103, R0912, R0915, E1101
# pylint: disable=too-many-instance-attributes, too-many-locals, no-self-use
# pylint: disable=bad-continuation, too-many-lines, too-many-public-methods
# pylint: disable=bare-except, broad-except
# pylint: disable=line-too-long
# pylint: disable=too-many-nested-blocks

# https://www.geeksforgeeks.org/python-programming-language/

import os
import sys
import argparse
import datetime
import tempfile

# import collections
# from time import gmtime, strftime
from dataclasses import dataclass
import regex as re  # for unicode support  (pip install regex)


def fatal(msg):
    """fatal error: print message and exit"""
    print("FATAL: {}".format(msg))
    sys.exit(1)


@dataclass
class W:
    """one object of this class for every unique word in book"""

    word: str  # the word
    where: set()  # all line numbers with this word
    checkas: str  # how it will be checked


def aggregate(b):
    """aggregation
    load the aggregation file
    combine this data set
    """
    hdata = {}
    t1 = open("aggregate.txt", "r", encoding="UTF-8").read()
    a = t1.split("\n")
    # put historical data in a map hdata
    for t in a:
        if t != "":
            c = t.split(",")
            hdata[c[0]] = int(c[1])

    for word in b:
        # is word from this project already in aggregate
        if word in hdata:
            # yes
            hdata[word] = hdata[word] + len(b[word].where)
        else:
            hdata[word] = len(b[word].where)

    # generate the report to file
    f = open("aggregate.txt", "w")
    for word in hdata:
        f.write("{},{}\n".format(word, hdata[word]))
    f.close()


def loadFile(fn):
    """
    load specified file
    source file can be UTF-8 or ISO-8859-1
    """
    if not os.path.isfile(fn):
        fatal("file {} not found".format(fn))
    try:
        wbuf = open(fn, "r", encoding="UTF-8").read()
        wbs = wbuf.split("\n")
        # remove BOM on first line if present
        t31 = ":".join("{0:x}".format(ord(c)) for c in wbs[0])
        if t31[0:4] == "feff":
            wbs[0] = wbs[0][1:]
    except UnicodeDecodeError:
        wbuf = open(fn, "r", encoding="ISO-8859-1").read()
        wbs = wbuf.split("\n")
    except Exception as e:
        fatal("file failed to load. ({})".format(e))
    while len(wbs) > 1 and wbs[-1] == "":  # no trailing blank lines
        wbs.pop()
    return wbs


def loadFromFile(fn):
    """load word file, protect internal punctuation, return as a list"""
    t32 = loadFile(fn)
    for i, _ in enumerate(t32):
        t32[i] = re.sub(r"--", r"≣≣", t32[i])  # old-style long dash (must be in pairs)

        # t32[i] = re.sub(
        #    r"([\p{L}\-])[’']([\p{L}\-])", r"\1ᒽ\2", t32[i]
        # )  # internal apostrophe
        # t32[i] = re.sub(r"([\p{L}\-])[’']([\p{L}\-])", r"\1ᒽ\2", t32[i])  # if overlapped
        t32[i] = re.sub(r"[’']", r"ᒽ", t32[i])  # any apostrophe

        t32[i] = re.sub(
            r"([\p{L}\-])‘([\p{L}\-])", r"\1ᒻ\2", t32[i]
        )  # turned comma "M‘Cord"
        t32[i] = re.sub(r"([\p{L}\-])‘]([\p{L}\-])", r"\1ᒻ\2", t32[i])  # if overlapped
        t32[i] = re.sub(r"([\p{L}\-])-([\p{L}\-])", r"\1ᗮ\2", t32[i])  # internal hyphen
        t32[i] = re.sub(r"([\p{L}\-])-([\p{L}\-])", r"\1ᗮ\2", t32[i])  # if overlapped
        # special case
        t32[i] = re.sub(r"%$", r"", t32[i])  # in wordlist signalling plural form
        t32[i] = re.sub(r"≣", r"-", t32[i])  # restore long dashᒽᒻᗮ
    return t32


def getWordSet(b):
    """build a dict of word objects
    keeps all apostrophes, even though a closing apos might be a close
    single quote. later, try to replace the apos with a letter (typ. 'g')
    to make a word.
    """
    a = b[:]  # local writeable copy
    wo = dict()  # word objects
    for i, _ in enumerate(a):
        t33 = a[i]
        t33 += " "  # add space so contraction tests work
        t33 = t33.replace("_", " ")  # remove italics markup
        t33 = t33.replace("=", " ")  # and bold
        t33 = re.sub(r"\P{L}", " ", t33)  # anything remaining that's not a letter
        a[i] = t33
    for i, line in enumerate(a):
        line = re.sub(r" +", " ", line)
        words = line.split(" ")
        # classify each word
        for word in words:
            if word == "":
                continue
            if word in wo:  # it is there, append to it
                lineset = wo[word].where
                lineset.add(i)
                wo[word] = W(word, lineset, "")
                # wo[word] = W(word, {wo[word].where,i})
            else:  # not there, create an object for this word
                wo[word] = W(word, {i}, "")
    return wo


wb = []  # list of lines of text, no modifications
gwl = {}  # set of good words, per project
swl = {}  # set of supplemental words, per PPer
gwll = {}  # set of good words, per project (lower case)
swll = {}  # set of supplemental words, per PPer (lower case)
wd = dict()

"""
main program
"""

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--infile", help="input file", required=True)
parser.add_argument("-o", "--outfile", help="output file", required=True)
parser.add_argument("-g", "--goodfile", help="good words file", required=False)
parser.add_argument("-s", "--suppfile", help="supplemental words file", required=False)
args = vars(parser.parse_args())

# load working buffer and word lists
wb = loadFromFile(args["infile"])  # user's unmodified text file

if args["goodfile"]:
    gwl = set(loadFromFile(args["goodfile"]))  # good word list (per project)
    gwll = [s.lower() for s in gwl]

if args["suppfile"]:
    swl = set(loadFromFile(args["suppfile"]))  # supplemental word list
    swll = [s.lower() for s in swl]

# From the working buffer, generate a dict of structures
wd = getWordSet(wb)

# some words may need small changes to validate
# the base or derived word for each key is in "checkas" string

# contractions
for key in wd:
    for cc in ["ᒽll", "ᒽve", "ᒽre", "ᒽd", "ᒽs"]:
        if key.endswith(cc):
            wd[key].checkas = re.sub(r"{}$".format(cc), "", key)  # will

# if any "checkas" is all caps, it may be a proper name
# if it has a title-case entry elsewhere, title-case the checkas string
# need to verify this is working as expected
for key in wd:
    if wd[key].checkas.upper() == wd[key].checkas:  # all caps
        if (
            wd[key].checkas.lower()
        ).title() in wd:  # is title case version in the dict?
            wd[key].checkas = (
                wd[key].checkas.lower()
            ).title()  # yes, so check as title case

# if any "checkas" is Title case, it may be a proper name
# if it has a lower-case entry elsewhere, downcase the checkas string
# example: "This is an example of how this works" will check "This" as
# the word "this".
for key in wd:
    if wd[key].checkas.title() == wd[key].checkas:
        if wd[key].checkas.lower() in wd:  # is lower case version in the dict?
            wd[key].checkas = wd[key].checkas.lower()  # yes, so check as lower-case

# aggregate into learning wordlist
# aggregate(wd)  already done

# begin reductions

# anything that hasn't been changed to a different checkas string
# should check the word as provided.
for key in wd:
    if wd[key].checkas == "":  # nothing yet
        wd[key].checkas = key

# reduce wd by words in the gwl (good word list)
# case insensitive
c = set()
for key in wd:
    t = wd[key].word
    if t in gwl:
        c.add(key)
    if t.lower() in gwll:
        c.add(key)
for item in c:
    del wd[item]

# reduce wd by words in the swl (supplemental word list)
# case insensitive
c = set()
for key in wd:
    t = wd[key].word
    if t in swl:  # in supplemental list
        c.add(key)  # mark for removal from suspects
    if t.lower() in swll:
        c.add(key)
for item in c:
    del wd[item]

# reduce by frequency of occurrence
# 3 or more times means good
c = set()
for key in wd:
    if len(wd[key].where) > 3:
        c.add(key)
for item in c:
    del wd[item]

# convert closing "inᒽ" to "ing" for checkas words
for key in wd:
    if key.endswith("inᒽ"):
        wd[key].checkas = key[:-1] + "g"

# reduce by dictionary lookup

# save all suspects

f1 = tempfile.NamedTemporaryFile(mode="w", delete=False)
f2 = tempfile.NamedTemporaryFile(mode="r", delete=False)
for key in wd:
    t = re.sub(r"ᒽ", "'", wd[key].checkas)
    t = re.sub(r"ᗮ", "-", t)
    f1.write(t + "\n")
f1.close()
os.system(
    "cat {} | aspell list --lang en,en_GB --encoding utf-8 > {}".format(
        f1.name, f2.name
    )
)
os.unlink(f1.name)

# get that list of unapproved words back
t = open(f2.name, "r", encoding="UTF-8").read()
os.unlink(f2.name)
# put unapproved words in new set

wd2 = dict()

t2 = t.split("\n")
tset = set(t2)
for key in wd:
    if wd[key].checkas in tset:
        wd2[key] = wd[key]

# there may be words like "sayin'" and "huntin'" and "plannin'"
# do these separately (and expensively)
# if the word without the "in'" is a word, and
# the word with the "in'" changed to "ing" is a word,
# then accept it as a contraction.
# special adjustment: if the word without the "in'" has the
# last letter repeated, then drop one of them to make testw1.
# "runnin'" -> ("run", "running")
# I cannot simply add a 'g' becuase that would wreck "insulin" or "vermin"
c = set()
for key in wd2:
    if key.endswith("in"):
        testw1 = key[:-2]
        if len(testw1) > 2 and testw1[-1] == testw1[-2]:
            testw1 = testw1[:-1]
        testw2 = key + "g"
        cmd = 'echo "{} {}" | aspell --list'.format(testw1, testw2)
        result = os.popen(cmd).read()
        if result == "":
            # both test words are okay. accept
            c.add(key)
for item in c:
    del wd2[item]

# generate the report to file
f = open(args["outfile"], "w", encoding="utf-8")
# f.write("\uFEFF")  # BOM
f.write("<pre>")
f.write("pgspell run report\n")
f.write(f"run started: {str(datetime.datetime.now())}\n")
f.write("source file: {}\n".format(os.path.basename(args["infile"])))
f.write(
    f"<span style='background-color:#FFFFDD'>close this window to return to the UWB.</span>\n"
)
f.write("\n")

for key, _ in sorted(wd2.items(), key=lambda x: x[0]):
    t = key.replace("ᒽ", "'")
    t = t.replace("ᒻ", "'")
    t = t.replace("ᗮ", "-")
    f.write("{}\n".format(t))
    for n in wd2[key].where:
        t = wb[n].replace("ᒽ", "'")
        t = t.replace("ᒻ", "'")
        t = t.replace("ᗮ", "-")
        f.write("   {}: {}\n".format(n, t))
f.write("</pre>")
f.close()
