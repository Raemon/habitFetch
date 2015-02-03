from sqlalchemy import Column, Table, Boolean, Integer, String, Float, ForeignKey, Sequence, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.associationproxy import association_proxy

engine = create_engine('sqlite:///:test.db:')

Base = declarative_base()

tags_tasks_association = Table('tags_tasks_association', Base.metadata,
    Column('tag_id', String, ForeignKey('tasks.id')),
    Column('task_id', String, ForeignKey('tags.id'))
)

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True)
    name = Column(String)
    #task_type should be either habit, daily or todo
    task_type = Column(String)
    date_created = Column(Float)
    date_completed = Column(Float)
    # notes = Column(String)

    #Many to many

    tags = relationship('Tag', 
                        secondary=tags_tasks_association,
                        backref='tasks')

    #One to many
    histories = relationship("History", backref='task')

    def __repr__(self):
        return "<Task(id='%s', name='%s', task_type='%s', date_created='%s', date_completed='%s', tags='%s')>" % (self.id, self.name, self.task_type, self.date_created, self.date_completed, self.tags)


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(String, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return "<Tag(id='%s', name='%s')>" % (self.id, self.name)


class History(Base):
    __tablename__ = 'histories'

    id = Column(Integer, primary_key=True)
    date_created = Column(Float)
    task_id = Column(String, ForeignKey('tasks.id'))
    checklist_items = relationship('ChecklistItem', backref='histories')

    # Should be 1, -1 or 0
    # If completed, marked 1
    # If it is a habit that was downvoted, marked 
    up_or_downvote = Column(Integer)

    # Value should range approximately from -20 to 10
    value = Column(Float)


    def __repr__(self):
        return "<History(id='%s', date_created='%s', task_id='%s', value='%s')>" % (self.id, self.date_created, self.task_id, self.value)



class ChecklistItem(Base):
    __tablename__ = 'checklist_items'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    completed = Column(Boolean)

    history_id = Column(String, ForeignKey('histories.id'))

    def __repr__(self):
        return "<ChecklistItem(history_id='%s', id='%s', name='%s', completed='%s')>" % (self.history_id, self.id, self.name, self.completed)

 