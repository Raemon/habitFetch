from __future__ import print_function

import sqlite3
import json
import time
import settings
import sqlalchemy
import sys

from habitrpg_api import HabitApi

hrpg = HabitApi(user_id = settings.user_id, api_key = settings.api_key)


print(json.dumps(hrpg.user(), sort_keys=True,indent=4))

# sys.stderr.write('spam\n')


print('spam', file=sys.stderr)
