import sqlalchemy as sql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref

engine = sql.create_engine('sqlite:///:test.db:')

Base = declarative_base()

class User(Base):
	__tablename__ = 'users'

	id = sql.Column(sql.String(), sql.Sequence('user_id_seq'), primary_key=True)
	name = sql.Column(sql.String(50))
	fullname = sql.Column(sql.String(50))
	password = sql.Column(sql.String(20))

	def __repr__(self):
		return "<User(name='%s', fullname='%s', password='%s')>" % (self.name, self.fullname, self.password)

class Address(Base):
	__tablename__ = 'addresses'
	id = sql.Column(sql.Integer, primary_key=True)
	email_address = sql.Column(sql.String, nullable=False)
	user_id = sql.Column(sql.Integer, sql.ForeignKey('users.id'))

	user = relationship("User", backref=backref('addresses', order_by=id))


Base.metadata.create_all(engine) 
Session = sessionmaker(bind=engine)
session = Session()

selection = session.query(User).all()
print "OLD NAMES _________________________________________________"
for user in selection:
	print user.id


session.add_all([
	User(id="qw2er-1234-asdf", name="wendy", fullname="Wendy Moira", password="pan"),
	User(id="qw4er-asdf-asdf", name="bob", fullname="Bob MacPharson", password="steve"),
	User(id="qwser-zxvc-asdf", name="foo", fullname="Foo Bar", password="foobarpassword")
	])

session.add_all([
	Address(email_address="test@qwer.com", user_id=1),
	])

session.commit()








