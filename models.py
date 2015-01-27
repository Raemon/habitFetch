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

    #Many to many

    tags = relationship('Tag', 
                        secondary=tags_tasks_association,
                        backref='tasks')
    

    #One to many
    histories = relationship("History", backref='task')
    checklist_items = relationship('ChecklistItem', backref='tasks')


    def __repr__(self):
        return "<Task(id='%s', date_created='%s'), name='%s', tags='%s')>" % (self.id, self.date_created, self.name, self.tags)


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

    # Value should range approximately from -20 to 10
    value = Column(Float)

    def __repr__(self):
        return "<History(id='%s', date_created='%s', task_id='%s', value='%s')>" % (self.id, self.date_created, self.task_id, self.value)

class ChecklistItem(Base):
    __tablename__ = 'checklist_items'

    id = Column(String, primary_key=True)
    name = Column(String)
    complete = Column(Boolean)

    task_id = Column(String, ForeignKey('tasks.id'))

    def __repr__(self):
        return "<ChecklistItem(id='%s', name='%s', task_id='%s', complete='%s')>" % (self.id, self.name, self.task_id, self.complete)

 