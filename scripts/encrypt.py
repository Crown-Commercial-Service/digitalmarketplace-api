#!/usr/bin/env python
""" Test encryption

Usage:
    encrypt.py <password>

Example:
    ./encrypt.py
"""
import bcrypt
from docopt import docopt

arguments = docopt(__doc__)

password = arguments['<password>']

hashed = bcrypt.hashpw(password, bcrypt.gensalt(10))

if bcrypt.hashpw(password, hashed) == hashed:
    print("It Matches!")
else:
    print("It Does not Match :(")
