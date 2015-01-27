import sqlite3
import json
import time
import settings
import sqlalchemy

from habitrpg_api import HabitApi
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_
from models import Task, Tag, History, ChecklistItem, Base

engine = sqlalchemy.create_engine('sqlite:///:habitrpg_data.db:')
Base.metadata.create_all(engine)

'''
Notes
If you do multiple habits in a short timespan, 
    it saves the old timestamp and updates it with new graph data
'''

def convert_date(old_timestamp):
    try:
        new_timestamp = float(old_timestamp)/1000
    except:
        new_timestamp = time.strptime(old_timestamp.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        new_timestamp = time.mktime(new_timestamp)
    return new_timestamp

def store_latest():
    hrpg = HabitApi(user_id = settings.user_id, api_key = settings.api_key)
    Session = sessionmaker(bind=engine)
    session = Session()

    print "-----------------------------------------------------------"
    print "----                 Checking Tags                     ----"
    print "-----------------------------------------------------------"
    for tag in hrpg.user()['tags']:
        print find_or_add_tag(session, id=tag['id'], name=tag['name'])


    print "-----------------------------------------------------------"
    print "----                 Checking Tasks                    ----"
    print "-----------------------------------------------------------"
    for task in hrpg.tasks():
        tags = [session.query(Tag).filter_by(id=x).first() for x in task['tags'].keys()]
        print "Id", task['id']
        print "Name,", task['text']
        print "Tags:", tags
        print add_task(
                session, 
                id=task['id'], 
                name=task['text'],
                task_type=task['type'],
                date_created=convert_date(task['dateCreated']),
                tags=tags)

        if task['type'] != "todo":
            for history in task['history']:

                print add_history(
                    session = session, 
                    date_created = history['date'], 
                    task_id = task['id'],
                    value = history['value']
                    )
        else:
            print "checklist: ", task['checklist']

        print ""


    for item in session.query(Tag).all():
        print item
    for item in session.query(Task).all():
        print item
    for item in session.query(History).all():
        print item

    session.close()

def find_or_add_tag(session, id, name):
    tag = session.query(Tag).filter_by(id=id).first()
    if tag == None:
        tag = Tag(id=id, name=name)
        session.add(tag)
        session.commit()
        return tag
    else:
        if name:
            if tag.name != name:
                tag.name = name
                session.commit()
        return session.query(Tag).filter_by(id=id).first()

def add_task(session, id, name, task_type, date_created, tags):
    task = session.query(Task).filter_by(id=id).first()
    if task == None:
        task = Task(id=id, name=name, task_type=task_type, date_created=date_created, tags=[])
        session.add(task)
        output = "New Task Created: "
    else:
        output = "Task already exists: "


    while task.tags:
        task.tags.pop()

    for tag in tags:
        try:
            task.tags.append(find_or_add_tag(session, tag.id, tag.name))
        except:
            print "Failed to add tags", tag
    print task
    session.commit()
    return output, task.name

def add_history(session, date_created, task_id, value):
    history = session.query(History). \
                                    filter_by(date_created=convert_date(date_created)). \
                                    filter_by(task_id=task_id). \
                                    filter_by(value=value).first()
    if history == None:
        converted_date = convert_date(date_created)
        history = History(date_created=converted_date, task_id=task_id, value=value)
        session.add(history)
        output = "New History Created: "
    else:
        output = "History already exists: "
    session.commit()
    return output, history


def add_checklist_item(session, id, name, complete, task_id):
    checklist_item = session.query(ChecklistItem).filter_by(id=id).first()
    session.commit()
    return output, checklist_item

store_latest()




# def add_task(id, name, task_type, date_created, tags):
#     conn.execute("SELECT * FROM Tasks WHERE name == ? AND timestamp == ? AND task_type == ? AND value == ?", (name, timestamp, task_type, value))
#     if len(conn.fetchall()) == 0:
#         print "adding task"
#         conn.execute("INSERT INTO Tasks (name, task_type, timestamp, value) VALUES (?,?,?,?)",(name, task_type, timestamp, value))
#         db.commit()
#         conn.execute("SELECT * FROM Tasks WHERE name == ? AND timestamp == ? AND task_type == ?", (name, timestamp, task_type))
#         # print "Number of Identical Tasks", len(conn.fetchall())
#     else:
#         # /\print "task history already exists"
#         pass


# def GetAllActivitiesOnDate(month,day,year):
#     start_time = time.mktime((year,month,day,0,0,0,0,0,0)) 
#     end_time = time.mktime((year,month,day,23,59,0,0,0,0)) #use 1 for last  argument if you live somewhere with dst
#     conn.execute("SELECT * FROM Activities WHERE timestamp > ? AND timestamp < ?",(start_time,end_time))
#     return conn.fetchall()


# for item in hrpg.user()['tags']:
#     print item

# for item in hrpg.user()['todos']:
#     print item['checklist']

# print ""

# for task in hrpg.tasks():
#     print task['text']
#     print task['type']
#     print task['tags']
#     print "---------"
#     for item in task:
#         print item
#         if item == "checklist":
#             print task["checklist"]
#     print ""





# for habit in hrpg.user()['habits']:
#     for date in habit['history']:
#         print date
#         add_task(str(habit['text']), str(habit['id']), "habit", convert_date(date['date']), date['value'])
#     print ""

# for daily in hrpg.user()['dailys']:
#     for date in daily['history']:
#         add_task(str(daily['text']), str(daily['id']), "daily", convert_date(date['date']), date['value'])  

# data = conn.execute("SELECT * FROM Tasks")
# for x in data:
#     print x


