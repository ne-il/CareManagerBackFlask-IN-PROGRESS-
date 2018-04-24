from app import db
from sqlalchemy.dialects.postgresql import JSON

class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String())
    result_all = db.Column(JSON)
    result_no_stop_words = db.Column(JSON)

    def __init__(self, url, result_all, result_no_stop_words):
        self.url = url
        self.result_all = result_all
        self.result_no_stop_words = result_no_stop_words

    def __repr__(self):
        return '<id {}>'.format(self.id)

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String())
    lastName = db.Column(db.String())

    def __init__(self, url, firstName, lastName):
        self.url = url
        self.firstName = firstName
        self.lastName = lastName

    def __repr__(self):
        return '<id {}, firstName{}, lastName{} >'.format(self.id, self.firstName, self.lastName)