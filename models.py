from app import db
from sqlalchemy.orm import relationship, backref
from marshmallow import Schema, fields, post_load
from marshmallow_enum import EnumField

from enum import Enum, auto


class AutoName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name


class DocumentType(AutoName):
    PRESCRIPTION = auto()
    RADIOGRAPH = auto()
    OBSERVATION = auto()


class NodeType(AutoName):
    ROOT = auto()
    HOSPITAL = auto()
    DIVISION = auto()
    HOSPITAL_UNIT = auto()
    CARE_UNIT = auto()


class DocumentStatus(AutoName):
    IN_PROGRESS = auto()
    VALIDATED = auto()


class StaffType(AutoName):
    DOCTOR = auto()
    NURSE = auto()
    SECRETARY = auto()
    ADMIN = auto()


# ================================================================================
class Node(db.Model):
    __tablename__ = 'nodes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    type = db.Column(db.Enum(NodeType))
    patients = relationship("Patient", back_populates="node")
    staffs = relationship("Staff", back_populates="node")
    parent_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    children = relationship("Node", backref=backref('parent', remote_side=[id]), cascade="all, delete-orphan")

    def __init__(self, name, type, parent_id):
        self.name = name
        self.type = type
        self.parent_id = parent_id

    def __repr__(self):
        return '<id: {}, name: {}, type: {} , parent_id: {}, children: \n\t{}>'.format(self.id, self.name, self.type, self.parent_id, self.children)


class NodeSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    type = fields.String()
    type = EnumField(NodeType, by_value=True)
    children = fields.Nested('self', many=True)
    parent_id = fields.Integer()

    @post_load
    def make_user(self, data):
        return Node(**data)
# ================================================================================

# ================================================================================
class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String())
    lastName = db.Column(db.String())
    social_security_number = db.Column(db.String())
    address = db.Column(db.String())
    birthdate = db.Column(db.Date())
    place_of_birth = db.Column(db.String())
    documents = relationship("Document", back_populates="patient")
    node = relationship("Node", back_populates="patients")
    node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))

    # def __init__(self, firstName, lastName, social_security_number, address, birthdate, place_of_birth, node_id):
    #     self.firstName = firstName
    #     self.lastName = lastName
    #     self.social_security_number = social_security_number
    #     self.address = address
    #     self.birthdate = birthdate
    #     self.place_of_birth = place_of_birth
    #     self.node_id = node_id

    def __repr__(self):
        return '<id: {}, firstName: {}, lastName: {}, social_security_number: {}, documents: {}, affected_node: {} >'.format(self.id, self.firstName, self.lastName, self.social_security_number, self.documents, self.node)

class PatientSchema(Schema):
    id = fields.Integer()
    firstName = fields.String()
    lastName = fields.String()
    social_security_number = fields.String()
    address = fields.String()
    birthdate = fields.Date()
    place_of_birth = fields.String()
    node_id = fields.Integer()

    @post_load
    def make_patient(self, data):
        return Patient(**data)


# ================================================================================


# ================================================================================
class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(DocumentType))
    status = db.Column(db.Enum(DocumentStatus))
    description = db.Column(db.String())
    url_image = db.Column(db.String())
    validation_ts = db.Column(db.TIMESTAMP)

    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'))
    patient = relationship("Patient", back_populates="documents")

    author_id = db.Column(db.Integer, db.ForeignKey('staffs.id'))
    author = relationship("Staff", back_populates="documents")

    def __init__(self, type, status, patient_id, author_id):
        self.type = type
        self.status = status
        # self.description = description
        # self.url_image = url_image
        self.patient_id = patient_id
        self.author_id = author_id

    def __repr__(self):
        return '<id: {}, patient_id: {}, author_id: {}, description: {}, status: {}, type: {} >'.format(self.id, self.patient_id, self.author_id,
                                                                                         self.description, self.status,
                                                                                         self.type)


class DocumentSchema(Schema):
    id = fields.Integer(required=True)
    type = EnumField(DocumentType, by_value=True)
    status = EnumField(DocumentStatus, by_value=True)
    description = fields.String()
    url_image = fields.String()
    validation_ts = fields.Time()
    patient = fields.Nested(PatientSchema)
    patient_id = fields.Integer(required=True)
# ================================================================================


# ================================================================================
class Staff(db.Model):
    __tablename__ = 'staffs'

    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String())
    lastName = db.Column(db.String())
    type = db.Column(db.Enum(StaffType))
    documents = relationship("Document", back_populates="author")
    node = relationship("Node", back_populates="staffs")
    node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))

    def __init__(self, firstName, lastName, type, node_id):
        self.firstName = firstName
        self.lastName = lastName
        self.type = type
        self.node_id = node_id

    def __repr__(self):
        return '\n <id {}, firstName: {}, lastName: {}, type: {}, node_id: {}>'.format(self.id, self.firstName, self.lastName, self.type, self.node_id)

class StaffSchema(Schema):
    id = fields.Integer()
    firstName = fields.String()
    lastName = fields.String()
    type = EnumField(StaffType, by_value=True)
    # node = fields.Nested(NodeSchema)
    node_id = fields.Integer()
# ================================================================================

