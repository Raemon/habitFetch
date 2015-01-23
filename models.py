from sqlalchemy import Column, Integer, String, Float, ForeignKey, Sequence, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref

engine = create_engine('sqlite:///:test.db:')

Base = declarative_base()

class User(Base):
	__tablename__ = 'users'

	id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
	name = Column(String)
	fullname = Column(String)
	password = Column(String)

	def __repr__(self):
		return "<User(name='%s', fullname='%s', password='%s')>" % (self.name, self.fullname, self.password)

class Task(Base):
	__tablename__ = 'tasks'
	id = Column(String, primary_key=True)
	name = Column(String)
	task_type = Column(String)
	date_created = Column(Float)
	tags = relationship("Tag", backref=backref('tasks', order_by=date_created))
	histories = relationship("History", backref='tasks')

	def __repr__(self):
		return "<Task(id='%s', name='%s', tags='%s', histories='%s')>" % (self.id, self.name, self.tags, self.histories)


class Tag(Base):
	__tablename__ = 'tags'

	id = Column(String, primary_key=True)
	name = Column(String)
	tasks = relationship("Task", backref=backref('tags', order_by=id))

	def __repr__(self):
		return "<Task(id='%s', name='%s', tasks='%s')>" % (self.id, self.name, self.tasks)


class History(Base):
	__tablename__ = 'histories'

	id = Column(Integer, primary_key=True)
	date_created = Column(Float)
	task_id = Column(String, ForeignKey('task.id'))
	task = relationship("Task", backref=backref('histories', order_by=date_created))

	value = Column(String)

Base.metadata.create_all(engine) 