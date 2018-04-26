from app import db
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

import enum

class DocumentType(enum.Enum):
    prescription = "PRESCRIPTION"
    radiograph = "RADIOGRAPH"
    observation = "OBSERVATION"

class DocumentStatus(enum.Enum):
    in_progress = "IN_PROGRESS"
    validated = "VALIDATED"

class StaffType(enum.Enum):
    doctor = "DOCTOR"
    nurse = "NURSE"
    secretary = "SECRETARY"
    admin = "ADMIN"


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
    documents = relationship("Document", back_populates="patient")

    def __init__(self, url, firstName, lastName):
        self.url = url
        self.firstName = firstName
        self.lastName = lastName

    def __repr__(self):
        return '<id {}, firstName{}, lastName{} >'.format(self.id, self.firstName, self.lastName)



class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    # author = db.Column(Staff)
    # patient = db.Column(Patient)

    patient = relationship("Patient", back_populates="documents")
    type = db.Column(db.Enum(DocumentType))
    status = db.Column(db.Enum(DocumentStatus))
    description = db.Column(db.String())
    url_image = db.Column(db.String())
    validation_ts = db.Column(db.TIMESTAMP);


    def __init__(self, id, patient, type, status, description, url_image):
        # self.author= author
        self.patient = patient
        self.type = type
        self.status = status
        self.description = description

    def __repr__(self):
        return '<id: {}, author{}, patient{}, description{}, status{} >'.format(self.id, self.author, self.patient, self.description, self.status)


# class Staff(db.Model):
#     __tablename__ = 'staffs'
#
#     id = db.Column(db.Integer, primary_key=True)
#     firstName = db.Column(db.String())
#     lastName = db.Column(db.String())
#     type = db.Column(db.Enum(StaffType))
#
#     def __init__(self, firstName, lastName, type):
#         self.firstName = firstName
#         self.lastName = lastName
#         self.type = type
#
#     def __repr__(self):
#         return '<id {}, firstName{}, lastName{}, type{} >'.format(self.id, self.firstName, self.lastName, self.type)



