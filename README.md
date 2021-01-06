# Vennt Discord Bot

**Requires**: d20, discord, requests, bs4, dotenv, time, datetime, json, random, os, sys, re, traceback, operator, math


**Usage**: `py -3 venntbot.py`


### Style

- Globals are in ALL_CAPS and restricted to the `db` module
- Internal functions deal in Entities, command functions deal in strings
- Internal functions deal in numbers, command functions must convert numeric args using `stats.clean_modifier(arg)`
- Internal versions of command functions are named `do_x`
- Each class builds its own copy of Logger: logging uses this instead of print statements
- Naming conventions:
  - who/target/attacker: the human-readable string referring to an entity, equivalent to `entity.display_name()`
  - e/ent/entity: the entity object for a player or enemy, equivalent to `db.find(who)`
  - *_ent: the object for a named entity, e.g. target_ent
- Data conventions:
  - Stats are in ALL_CAPS (ACC, VIM, HP) and get converted immediately
  - Entity names are unchanged
  - Effect descriptions are in lower_case and get converted immediately
