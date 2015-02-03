# from __future__ import print_function

import sqlite3
import json
import time
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
        tags = [session.query(Tag).filter_by(id=x).first() for x in task['tags'].keys()]
        # print "TASK:", task
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

        try:
            histories = task['history']
        except:
            histories = [{'date': int(time.time()*1000), 'value':0}]

        print "histories:", histories
        for history in histories:
            new_history = add_history(
                session = session, 
                date_created = convert_date(history['date']), 
                task_id = task['id'],
                value = history['value']
                )
            print new_history.date_created

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
        '''
        else:
            date_created = time.time()
            history = add_history(
                session = session,
                date_created=date_created,
                task_id = task['id'],
                value = task['value'],
                )
            try:
                for checklist_item in task['checklist']:
                    add_checklist_item(
                        session=session,
                        id = checklist_item['id'],
                        name = checklist_item['text'],
                        date_created = convert_date(history['date']), 
                        history_id = history.id,
                        completed = checklist_item['completed'],
                        )
            except:
                pass
        '''
    except:
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, " "

def store_latest():
    hrpg = HabitApi(user_id = settings.user_id, api_key = settings.api_key)
    Session = sessionmaker(bind=engine)
    session = Session()

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
    # for task in session.query(Task).all():
    #     print task
    #     for history in session.query(History).filter_by(task_id=task.id).all():
    #         print "    ", history    
    #         for checklist_item in session.query(ChecklistItem).filter_by(history_id=history.id).all():
    #             print "        ", checklist_item

    for history in session.query(History).all():
        print history.date_created
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

        for tag in tags:
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
        history = session.query(History). \
                                        filter_by(date_created=convert_date(date_created)). \
                                        filter_by(task_id=task_id). \
                                        filter_by(value=value).first()

        # previous_history = session.query(History). \
        #                                 order_by(date_created=convert_date(date_created)). \
        #                                 filter_by(task_id=task_id). \
        #                                 filter_by(value=value)
        # print "previous_history", previous_history

        if history == None:
            converted_date = convert_date(date_created)
            history = History(date_created=converted_date, task_id=task_id, value=value)
            session.add(history)
            output = "New History Created: "
        else:
            output = "History already exists: "
        session.commit()
        return history
    except:
        print >> sys.stderr, "Failed to add History"
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, " "

def add_checklist_item(session, name, completed, history_id):
    try:
        checklist_item = session.query(ChecklistItem).\
            filter_by(history_id=history_id).\
            filter_by(name=name).first()
        if checklist_item == None:
            checklist_item = ChecklistItem(
                name=name, 
                completed=completed, 
                history_id=history_id
                )
            session.add(checklist_item)
            output = "New ChecklistItem Created"
        else:
            output = "ChecklistItem already exists"
        session.commit()
        print >> sys.stdout, output, checklist_item
        return checklist_item
    except:
        print >> sys.stderr, "Error while adding checklist"
        traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, " "

store_latest()