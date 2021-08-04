# pgspell
spell-check text analysis program used before/during upload to Project Gutenberg.
It may be used standalone by cloning this repo locally. It is also
part of the Uploader's Workbench (UWB) at Project Gutenberg.

## Overview

This is a Python program used to analyze the spelling of English words
in a UTF-8 text file. It accepts a text file and produces a report file
in HTML for display in a browser, where color-coding may be used.

## Usage

### Standalone

As a standalone program use this command line:

    python3 pgspell.py -i sourcefile.txt -o report.htm

You may also include "-v" to get verbose reports.

### In the UWB

This is one of the tests available in the
[UWB](https://uwb.pglaf.org).
It uses the Linux aspell dictionary.
You must have a user account on the pglaf server to use the UWB.

## Requirements

This program uses an internal aspell dictionary ("en,en-GB"). A version of this file
that uses a built-in wordlist is planned for those without aspell.

