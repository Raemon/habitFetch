from sqlalchemy import Column, Table, Boolean, Integer, String, Float, ForeignKey, Sequence, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref

engine = create_engine('sqlite:///:test.db:')

Base = declarative_base()

tags_tasks_association_table = Table('tags_tasks_association', Base.metadata,
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
						secondary=tags_tasks_association_table,
						backref='tasks')

	#One to many
	histories = relationship("History", backref='task')
	checklist_items = relationship('ChecklistItem', backref='task')

	def __repr__(self):
		return "<Task(id='%s', name='%s', date_created='%s')>" % (self.id, self.name, self.date_created)


class Tag(Base):
	__tablename__ = 'tags'

	id = Column(String, primary_key=True)
	name = Column(String)

	def __repr__(self):
		return "<Task(id='%s', name='%s'>" % (self.id, self.name)


class History(Base):
	__tablename__ = 'histories'

	id = Column(Integer, primary_key=True)
	date_created = Column(Float)
	task_id = Column(String, ForeignKey('tasks.id'))

	value = Column(String)

	def __repr__(self):
		return "<History(id='%s', date_created='%s', tasks='%s')>" % (self.id, self.name, self.tasks)

class ChecklistItem(Base):
	__tablename__ = 'checklist_items'

	id = Column(String, primary_key=True)
	name = Column(String)
	complete = Column(Boolean)

	task_id = Column(String, ForeignKey('tasks.id'))

Base.metadata.create_all(engine) 