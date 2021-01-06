# Vennt Discord Bot

**Requires**: d20, discord, requests, bs4, dotenv, time, datetime, json, random, os, sys, re, traceback, operator, math


**Usage**: `py -3 venntbot.py`


### Style

- Globals are in ALL_CAPS and restricted to the `db` module
- Internal functions deal in Entities, external (i.e. command) functions deal in strings
- Each class builds its own copy of Logger: logging uses this instead of print statements
