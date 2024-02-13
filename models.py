from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

# Database
db = SQLAlchemy()

''' Users model '''
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100))
    pw_hash = db.Column(db.String(200), nullable=False)
    privilege = db.Column(db.Integer, db.ForeignKey("privileges.id"))
    date = db.Column(db.DateTime, default=datetime.now())

    @property
    def password(self):
        raise AttributeError("Password is not readable attribute!")
    
    @password.setter
    def password(self, password):
        self.pw_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def __repr__(self) -> str:
        return self.username

''' Privileges model - User roles '''
class Privileges(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    users = db.relationship("Users", backref="role")

    def __repr__(self) -> str:
        return self.name

''' Cards model '''
class Cards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.Integer)
    card_label = db.Column(db.String(10), nullable=False)
    card_type = db.Column(db.String(5), nullable=False)
    card_location = db.Column(db.Integer, db.ForeignKey("reporters.id"))
    card_ingests = db.relationship('Ingests', backref='card')

    def __repr__(self) -> str:
        return self.card_label + str(self.card_number)
        

''' Reporters model '''
class Reporters(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    inventory = db.relationship('Cards', backref='owner')
    reporter_ingests = db.relationship('Ingests', backref='reporter')

    def __repr__(self) -> str:
        return self.name
    

''' Ingests model '''
class Ingests(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    for_day = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)
    by_reporter = db.Column(db.Integer, db.ForeignKey("reporters.id"), nullable=False)
    card_used = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
    time = db.Column(db.DateTime, default=datetime.now())
    info = db.Column(db.Text, default=None)
    number = db.Column(db.Integer, nullable=False)
    equip_label = db.Column(db.String(20), nullable=False)
    clip_start = db.Column(db.Integer, nullable=False)
    clip_end = db.Column(db.Integer, nullable=False)
    equip_operator = db.Column(db.String(20), nullable=False)

    def __repr__(self) -> str:
        return f"{self.day} - {self.reporter} - {self.card}"


''' Shooting Days model '''
class Days(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    date = db.Column(db.DateTime, nullable=False)
    day_ingests = db.relationship('Ingests', backref='day')

    def __repr__(self) -> str:
        return self.name
