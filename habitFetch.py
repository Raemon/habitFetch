# from __future__ import print_function

import sqlite3
import json
import time
import datetime
import settings
import sqlalchemy
import sys
import traceback

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

print "date", convert_date("2014-06-11T02:24:54.590Z")

def process_task(session, task):
    try:
        # Warning: Tasks with old, deleted tags will not retain data about those tagstag
        tags = [session.query(Tag).filter_by(id=x).first() for x in task['tags'].keys()]


        # print json.dumps(task, sort_keys=True,indent=4)
        # Todo tasks have a "date_completed" attribute, others do not
        try:
            date_completed = convert_date(task['dateCompleted'])
        except:
            date_completed = None
            
        add_task(session, 
            id=task['id'], 
            name=task['text'],
            task_type=task['type'],
            date_created=convert_date(task['dateCreated']),
            date_completed=date_completed,
            tags=tags)

        # By default, it creates one history item with today's date. 
        # If the task has at least one history of it's own, instead it creates histories based on those
        year = time.gmtime(time.time()).tm_year
        month = time.gmtime(time.time()).tm_mon
        day = time.gmtime(time.time()).tm_mday
        date_created = time.mktime(datetime.datetime(year, month, day).timetuple())*1000
        histories = [{'date': date_created, 'value':0}]
        try:
            if len(task['history']) != 0:
                histories = task['history']
        except:
            pass

        print "    histories:", histories

        for history in histories:
            new_history = add_history(
                session = session, 
                date_created = convert_date(history['date']), 
                task_id = task['id'],
                value = history['value']
                )

            try:
                for checklist_item in task['checklist']:
                    add_checklist_item(
                        session=session,
                        name = checklist_item['text'],
                        history_id = new_history.id,
                        completed = checklist_item['completed'],
                        )
            except:
                pass
            print ""
    except:
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, " "

def store_latest():
    hrpg = HabitApi(user_id = settings.user_id, api_key = settings.api_key)

    json.dumps(hrpg.user())
    Session = sessionmaker(bind=engine)
    session = Session()

    print "tag count:", session.query(Tag).count()
    print "task count:", session.query(Task).count() 
    print "history count:", session.query(History).count() 
    print "checklist_item count:", session.query(ChecklistItem).count() 

    print "----                 Checking Tags                     ----"
    for tag in hrpg.user()['tags']:
        print find_or_add_tag(session, id=tag['id'], name=tag['name'])

    print "----                 Checking Tasks                    ----"
    for task in hrpg.tasks():
        process_task(session, task)

    print "---------------------TAGS IN DATABASE---------------------"
    for item in session.query(Tag).all():
        print item
    print "---------------------TASKS IN DATABASE--------------------"   
    for task in session.query(Task).all():
        print task
        for history in session.query(History).filter_by(task_id=task.id).all():
            print "    ", history    
            for checklist_item in session.query(ChecklistItem).filter_by(history_id=history.id).all():
                print "        ", checklist_item

    print "tag count:", session.query(Tag).count()
    print "task count:", session.query(Task).count() 
    print "history count:", session.query(History).count() 
    print "checklist_item count:", session.query(ChecklistItem).count() 
    session.close()

def find_or_add_tag(session, id, name):
    try:
        # Does the tag ID exist already?
        tag = session.query(Tag).filter_by(id=id).first()

        # If not, create it
        if tag == None:
            tag = Tag(id=id, name=name)
            session.add(tag)
            session.commit()
            return tag

        # If so, update the tag's name to latest data, then return it
        else:
            if name:
                if tag.name != name:
                    tag.name = name
                    session.commit()
            return session.query(Tag).filter_by(id=id).first()
    except:
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, " "

def add_task(session, id, name, task_type, date_created, date_completed, tags):
    try:
        task = session.query(Task).filter_by(id=id).first()
        if task == None:
            task = Task(id=id, name=name, task_type=task_type, date_created=date_created, tags=[])
            session.add(task)
            output = "New Task Created: "
        else:
            output = "Task already exists: "

        while task.tags:
            task.tags.pop()

        print "tags:", tags
        for tag in tags:
            if tag != None:
                try:
                    task.tags.append(find_or_add_tag(session, tag.id, tag.name))
                    print >> sys.stdout, "Added tag", tag
                except:
                    traceback.print_exc(file=sys.stderr)
                    print >> sys.stderr, "Failed to add tag", tag

        session.commit()
        print >> sys.stdout, output, task.name
        return task
    except:
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, " "

def add_history(session, date_created, task_id, value):
    try:
        history = session.query(History).filter_by(date_created=date_created).filter_by(task_id=task_id).filter_by(value=value).first()
        print "HISTORY??:", history

        if history == None:

            previous_history = session.query(History). \
                                            order_by(History.date_created.desc()). \
                                            filter_by(task_id=task_id).first()
            adjust = 0
            if previous_history:
                if previous_history.value < value:
                    adjust = 1
                if previous_history.value > value:
                    adjust = -1
                print "previous_history: ", adjust

            history = History(date_created=date_created, task_id=task_id, adjust=adjust, value=value)
            session.add(history)
            output = "    New History Created: "
        else:
            output = "    History already exists: "
        print >> sys.stdout, output, history.date_created   
        session.commit()
        return history
    except:
        print >> sys.stderr, "Failed to add History"
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, " "

def add_checklist_item(session, name, completed, history_id):
    try:
        checklist_item = session.query(ChecklistItem).filter_by(history_id=history_id).filter_by(name=name).first()
        if checklist_item == None:
            checklist_item = ChecklistItem(
                name=name, 
                completed=completed, 
                history_id=history_id
                )
            session.add(checklist_item)
            output = "    New ChecklistItem Created"
        else:
            output = "    ChecklistItem already exists"
        session.commit()
        print >> sys.stdout, output, checklist_item
        return checklist_item
    except:
        print >> sys.stderr, "Error while adding checklist"
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, " "

store_latest()