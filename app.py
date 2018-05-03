import os
import decimal
import datetime
from flask import Flask, jsonify, request, Response
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import *

def alchemyencoder(obj):
    """JSON encoder function for SQLAlchemy special classes."""
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)

ALLOWED_DOC_TYPE_NURSE = [DocumentType.OBSERVATION]

documentSchema = DocumentSchema()
documentsSchema = DocumentSchema(many=True)
patientSchema = PatientSchema()
patientsSchema = PatientSchema(many=True)

nodeSchema = NodeSchema()
nodesSchema = NodeSchema(many=True)

@app.route('/')
def hello():
    return str(os.environ['APP_SETTINGS'])

@app.route('/<name>')
def hello_name(name):
    return "Hello  {}!".format(name)


# @app.route('/patients/<firstname>')
# def get_patient_by_firstname(firstname):
#     p = Patient.query.filter_by(firstName=firstname).first()
#
#     dicta = dict(p)
#     # dicts = [dict(r) for r in patients]
#     return json.dumps(dicta, default=alchemyencoder)


# NODE
# ================================================================================

def check_node_hierarchy(new_node, father_node):
    if father_node is None or new_node is None:
        return False
    if(new_node.type == NodeType.HOSPITAL and father_node.type == NodeType.ROOT):
        return True
    elif(new_node.type == NodeType.DIVISION and father_node.type == NodeType.HOSPITAL):
        return True
    elif (new_node.type == NodeType.HOSPITAL_UNIT and father_node.type == NodeType.DIVISION):
        return True
    elif (new_node.type == NodeType.CARE_UNIT and father_node.type == NodeType.HOSPITAL_UNIT):
        return True

    return False

@app.route("/nodes/<id>", methods=["GET"])
def get_node(id):
    node = Node.query.get(id)
    if (node is None):
        return "node_id doesn't match any node", 400
    node_details = nodeSchema.dump(node).data
    return jsonify(node_details)

@app.route("/nodes", methods=["GET"])
def get_all_nodes():
    nodes = Node.query.all()
    nodes_list = nodesSchema.dump(nodes).data
    return jsonify(nodes_list)


@app.route("/nodes", methods=["POST"])
def post_node():
    client_request = request.json
    result = nodeSchema.load(client_request)

    if(len(result.errors) != 0):
        return jsonify(result.errors), 400

    new_node = result.data
    father_node = Node.query.get(new_node.parent_id)

    if(father_node is None):
        return "parent_id doesn't match any node", 400
    if not check_node_hierarchy(new_node, father_node):
        return "Incompatible NodeType with fatherNode's NodeType: Tree hierarchy violated", 400

    db.session.add(new_node)
    db.session.commit()
    return jsonify(new_node), 200

# PATIENT
# ================================================================================

@app.route("/patients/<id>", methods=["GET"])
def get_patient_with_related_documents(id):
    requested_patient = Patient.query.get(id)
    asking_staff = Staff.query.filter_by(type=StaffType.SECRETARY).first()
    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type == StaffType.ADMIN):
        return "Admins are not allowed to get information about patients", 401
    if (requested_patient is None):
        return "patient_id doesn't match any patient", 400

    patient_details = patientSchema.dump(requested_patient).data

    if(asking_staff.type == StaffType.DOCTOR):
        doc_list = Document.query.filter_by(patient_id=requested_patient.id, status=DocumentStatus.VALIDATED)
    elif(asking_staff.type == StaffType.NURSE):
        doc_list = Document.query.filter_by(patient_id=requested_patient.id, status=DocumentStatus.VALIDATED)
        doc_list = list(filter(lambda x: x.type in ALLOWED_DOC_TYPE_NURSE, doc_list))
    elif (asking_staff.type == StaffType.SECRETARY):
        doc_list = []

    patient_documents = documentsSchema.dump(doc_list).data
    patient_details["documents"] = patient_documents
    return jsonify(patient_details), 200


def walk_through_tree(node):
    print(node.name)
    patient_of_node = []
    l = Patient.query.filter_by(node_id=node.id).all()
    for n in node.children:
        l.extend( walk_through_tree(n) )
    return l

@app.route("/patients", methods=["GET"])
def get_related_patients():
    asking_staff = Staff.query.filter_by(firstName="ROOTMAN").first()
    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type == StaffType.ADMIN):
        return "Admins are not allowed to acces any information about patients", 401


    staff_node = asking_staff.node
    if (staff_node is None):
        return "Can't find asking staff node", 500

    related_patients = walk_through_tree(staff_node)
    response_patients_list = patientsSchema.dump(related_patients).data

    return jsonify(response_patients_list), 200


def check_new_patient_integrity(new_patient):
    new_patient_node = Node.query.get(new_patient.node_id)
    if(new_patient_node is None):
        return False, "new_patient's node_id doesn't match any node"
    if(new_patient_node.type != NodeType.CARE_UNIT):
        return False, "A patient can ONLY be affected to a CARE_UNIT node !!"

    return True, "new_patient is valid"


@app.route("/patients", methods=["POST"])
def post_patient():
    client_request = request.json
    load_result = patientSchema.load(client_request)

    if(len(load_result.errors) != 0):
        return jsonify(load_result.errors), 400

    new_patient = load_result.data

    status, message = check_new_patient_integrity(new_patient)
    if(status == False):
        return message, 400

    db.session.add(new_patient)
    db.session.commit()
    response = patientSchema.dump(new_patient).data
    return jsonify(response), 200
# ================================================================================


# @app.route('/patients/<id>')
# def get_patient(id):
#     p = Patient.query.get(id)
#
#     patient_details = patientSchema.dump(p)
#     patient_documents = documentsSchema.dump(p.documents)
#
#     return jsonify({'patient_details': patient_details, 'patient_documents': patient_documents})

@app.route('/documents/<id>')
def get_document_by_id(id):
    document = Document.query.get(id)

    result = DocumentSchema().dump(document)
    return jsonify(result)


@app.route('/cleanAll')
def cleanAll():
    documents = Document.query.all()
    for d in documents:
        db.session.delete(d)

    patients = Patient.query.all()
    for p in patients:
        db.session.delete(p)

    db.session.commit()
    return "OK"

@app.route('/cleanPatient')
def cleanPatient():
    patients = Patient.query.all()
    for p in patients:
        db.session.delete(p)

    db.session.commit()
    return "OK"

@app.route('/cleanDocument')
def cleanDocument():
    documents = Document.query.all()
    for d in documents:
        db.session.delete(d)

    db.session.commit()
    return "OK"

@app.route('/fillPatient')
def fillPatient():
    p1 = Patient("Neil", "Anteur")
    p2 = Patient("Riad", "Anteur")
    p3 = Patient("Kenzi", "Anteur")
    p4 = Patient("Sid", "Anteur")
    p5 = Patient("Djalila", "Anteur")

    patients = list()
    patients.append(p1)
    patients.append(p2)
    patients.append(p3)
    patients.append(p4)
    patients.append(p5)

    for p in patients:
        db.session.add(p)
    db.session.commit()
    return "OK"

@app.route('/fillDocument')
def fillDocument():
    d1 = Document(DocumentType.PRESCRIPTION, DocumentStatus.IN_PROGRESS, "decription 1")
    d2 = Document(DocumentType.OBSERVATION, DocumentStatus.IN_PROGRESS, "decription 2")
    d3 = Document(DocumentType.OBSERVATION, DocumentStatus.IN_PROGRESS, "decription 3")
    d4 = Document(DocumentType.OBSERVATION, DocumentStatus.IN_PROGRESS, "decription 4")
    d5 = Document(DocumentType.OBSERVATION, DocumentStatus.IN_PROGRESS, "decription 5")

    neil = Patient.query.filter_by(firstName="Neil", lastName="Anteur").first()
    neil.documents.append(d1)
    neil.documents.append(d2)
    neil.documents.append(d3)
    neil.documents.append(d4)
    neil.documents.append(d5)
    # for p in patients:
    #     db.session.add(p)
    db.session.commit()
    return "OK"

if __name__ == '__main__':
    app.run()



# SELECT:
# target_patient = Patient.query.filter_by(firstName=«Neil», lastName=«Anteur»).first()
# all_patients = Patient.query.all()
#
#
# UPDATE:
# target_patient = Patient.query.filter_by(firstName='Neil', lastName='Anteur').first()
# target_patient= « CROTTE»
# db.session.commit()
#
# DELETE:
# target_patient = Patient.query.filter_by(firstName='Neil', lastName='Anteur').first()
# db.session.delete(target_patient)
