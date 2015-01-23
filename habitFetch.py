import requests
import sqlite3
import json
import time
import settings
import habitrpg_api


db = sqlite3.connect("habitRPG_data.sql") #you can put whatever ... created if not exist
conn = db.cursor()

'''
Notes
If you do multiple habits in a short timespan, 
    it saves the old timestamp and updates it with new graph data
'''

class HabitApi(object):
    DIRECTION_UP = "up"
    DIRECTION_DOWN = "down"

    TYPE_HABIT = "habit"
    TYPE_DAILY = "daily"
    TYPE_TODO = "todo"
    TYPE_REWARD = "reward"

    def __init__(self, user_id, api_key, base_url = "https://habitrpg.com/"):
        self.user_id = user_id
        self.api_key = api_key
        self.base_url = base_url

    def auth_headers(self):
        return {
            'x-api-user': self.user_id,
            'x-api-key': self.api_key
        }

    def request(self, method, path, *args, **kwargs):
        path = "%s/%s" % ("api/v1", path) if not path.startswith("/") else path[1:]

        if not "headers" in kwargs:
            kwargs["headers"] = self.auth_headers()

        return getattr(requests, method)(self.base_url + path, *args, **kwargs)

    def user(self):
        return self.request("get", "user").json()

    def tasks(self):
        return self.request("get", "user/tasks").json()

    def task(self, task_id):
        return self.request("get", "user/task/%s" % task_id).json()

    def create_task(self, task_type, text, completed = False, value = 0, note = ""):
        data = {
            'type': task_type,
            'text': text,
            'completed': completed,
            'value': value,
            'note': note
        }

        return self.request("post", "user/task/%s" % task_id, data=data).json()

    def update_task(self, task_id, text):
        return self.request("put", "user/task/%s" % task_id, data=text).json()

    def perform_task(self, task_id, direction):
        url = "/v1/users/%s/tasks/%s/%s" % (self.user_id, task_id, direction)
        data = json.dumps({'apiToken': self.api_key})
        headers={'Content-Type': 'application/json'}

        return self.request("post", url, data=data, headers=headers).json()


hrpg_access = HabitApi(user_id = settings.user_id, api_key = settings.api_key)

conn.execute("CREATE TABLE IF NOT EXISTS Tasks (name text, task_type text, timestamp int, value float);")

def add_task(name, task_id, task_type, timestamp, value):
    conn.execute("SELECT * FROM Tasks WHERE name == ? AND timestamp == ? AND task_type == ? AND value == ?", (name, timestamp, task_type, value))
    if len(conn.fetchall()) == 0:
        print "adding task"
        conn.execute("INSERT INTO Tasks (name, task_type, timestamp, value) VALUES (?,?,?,?)",(name, task_type, timestamp, value))
        db.commit()
        conn.execute("SELECT * FROM Tasks WHERE name == ? AND timestamp == ? AND task_type == ?", (name, timestamp, task_type))
        # print "Number of Identical Tasks", len(conn.fetchall())
    else:
        # /\print "task history already exists"
        pass


# def GetAllActivitiesOnDate(month,day,year):
#     start_time = time.mktime((year,month,day,0,0,0,0,0,0)) 
#     end_time = time.mktime((year,month,day,23,59,0,0,0,0)) #use 1 for last  argument if you live somewhere with dst
#     conn.execute("SELECT * FROM Activities WHERE timestamp > ? AND timestamp < ?",(start_time,end_time))
#     return conn.fetchall()

for item in hrpg_access.user()['tags']:
    print item

print ""


for task in hrpg_access.tasks():
    print task['text']
    print task['type']
    print task['tags']
    print "---------"
    for item in task:
        print item
        if item == "checklist":
            print task[item]
    print ""



def convert_date(old_timestamp):
    try:
        new_timestamp = float(old_timestamp)/1000
    except:
        new_timestamp = time.strptime(old_timestamp.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        new_timestamp = time.mktime(new_timestamp)
    return new_timestamp

for habit in hrpg_access.user()['habits']:
    for date in habit['history']:
        print date
        add_task(str(habit['text']), str(habit['id']), "habit", convert_date(date['date']), date['value'])
    print ""

for daily in hrpg_access.user()['dailys']:
    for date in daily['history']:
        add_task(str(daily['text']), str(daily['id']), "daily", convert_date(date['date']), date['value'])  

data = conn.execute("SELECT * FROM Tasks")
for x in data:
    print x


