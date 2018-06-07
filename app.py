import uuid

import os
import decimal
import datetime
from flask import Flask, jsonify, request, Response, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt
from sqlalchemy import exc

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

staffSchema = StaffSchema()
staffsSchema = StaffSchema(many=True)

nodeSchema = NodeSchema()
nodesSchema = NodeSchema(many=True)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            asking_staff = Staff.query.filter_by(public_id=data['public_id']).first()
        except:
            return jsonify({'message' : 'Token is invalid!'}), 401

        return f(asking_staff, *args, **kwargs)

    return decorated


@app.route('/')
def hello():
    return str(os.environ['APP_SETTINGS'])

@app.route('/<name>')
def hello_name(name):
    return "Hello  {}!".format(name)




# NODE
# ================================================================================


def is_a_child_node(father_node, child_node):
    for n in father_node.children:
        return n == child_node or is_a_child_node(n, child_node)
    return False

def is_a_child_node_recursive_correction(father_node, target_node):
    if(father_node == target_node):
        return True
    res = False
    for i in range(len(father_node.children)):
        if(res):
            break
        res = is_a_child_node_recursive_correction(father_node.children[i], target_node)
    return res


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

@app.route("/nodes/tree", methods=["GET"])
def get_tree():
    node = Node.query.filter_by(type=NodeType.ROOT).all()
    if (node is None):
        return "Can't find node ROOT", 400
    # node_details = nodeSchema.dump(node).data
    nodes_list = nodesSchema.dump(node).data
    return jsonify(nodes_list)
    # return jsonify(node_details)

@app.route("/nodes", methods=["GET"])
def get_all_nodes():
    nodes = Node.query.all()
    nodes_list = nodesSchema.dump(nodes).data
    return jsonify(nodes_list)

@app.route("/nodes/care_units", methods=["GET"])
def get_care_unit():
    nodes = Node.query.filter_by(type=NodeType.CARE_UNIT).all()
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
    node_info = nodeSchema.dump(new_node).data
    return jsonify(node_info), 200




# PATIENT
# ================================================================================

# OK
@app.route("/patients/<id>", methods=["GET"])
@token_required
def get_patient_with_related_documents(asking_staff, id):
    requested_patient = Patient.query.get(id)
    # asking_staff = Staff.query.filter_by(type=StaffType.SECRETARY).first()
    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type == StaffType.ADMIN):
        return "Admins are not allowed to get information about patients", 401
    if (requested_patient is None):
        return "patient_id doesn't match any patient", 400

    if not is_a_child_node_recursive_correction(asking_staff.node, requested_patient.node):
        return "this staff member is not allowed to see information about this patient (The patient is in a Care Unit you are not in charge of)", 401


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


def walk_through_tree_related_patients(node):
    print(node.name)
    patient_of_node = []
    l = Patient.query.filter_by(node_id=node.id).all()
    for n in node.children:
        l.extend(walk_through_tree_related_patients(n))
    return l

# OK
@app.route("/patients", methods=["GET"])
@token_required
def get_related_patients(asking_staff):
    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type == StaffType.ADMIN):
        return "Admins are not allowed to acces any information about patients", 401


    staff_node = asking_staff.node
    if (staff_node is None):
        return "Can't find asking staff node", 500

    related_patients = walk_through_tree_related_patients(staff_node)
    response_patients_list = patientsSchema.dump(related_patients).data

    return jsonify(response_patients_list), 200


def check_patient_integrity(new_patient):
    new_patient_node = Node.query.get(new_patient.node_id)
    if(new_patient_node is None):
        return False, "new_patient's node_id doesn't match any node"
    if(new_patient_node.type is not None and new_patient_node.type != NodeType.CARE_UNIT):
        return False, "A patient can ONLY be affected to a CARE_UNIT node !!"

    return True, "new_patient is valid"

@app.route("/patients", methods=["POST"])
@token_required
def post_patient(asking_staff):
    client_request = request.json
    load_result = patientSchema.load(client_request)

    if(len(load_result.errors) != 0):
        return jsonify(load_result.errors), 400

    new_patient = load_result.data

    status, message = check_patient_integrity(new_patient)
    if(status == False):
        return message, 400

    db.session.add(new_patient)
    db.session.commit()
    response = patientSchema.dump(new_patient).data
    return jsonify(response), 200


@app.route("/patients/<id>", methods=["PUT"])
@token_required
def update_patient(asking_staff, id):
    client_request = request.json

    patient_to_update = Patient.query.get(id)
    if (patient_to_update is None):
        return "patient_id doesn't match any patient in the database", 400

    load_result = patientSchema.load(client_request)
    if (len(load_result.errors) != 0):
        return jsonify(load_result.errors), 400

    new_patient = load_result.data

    patient_to_update.firstName = new_patient.firstName if new_patient.firstName is not None else patient_to_update.firstName
    patient_to_update.lastName = new_patient.lastName if new_patient.lastName is not None else patient_to_update.lastName
    patient_to_update.social_security_number = new_patient.social_security_number if new_patient.social_security_number is not None else patient_to_update.social_security_number
    patient_to_update.address = new_patient.address if new_patient.address is not None else patient_to_update.address
    patient_to_update.place_of_birth = new_patient.place_of_birth if new_patient.place_of_birth is not None else patient_to_update.place_of_birth
    patient_to_update.birthdate = new_patient.birthdate if new_patient.birthdate is not None else patient_to_update.birthdate
    patient_to_update.node_id = new_patient.node_id if new_patient.node_id is not None else patient_to_update.node_id

    status, message = check_patient_integrity(patient_to_update)
    if (status == False):
        db.session.roolback()
        return message, 400

    response = patientSchema.dump(patient_to_update).data
    db.session.commit()
    return jsonify(response), 200

# DOCUMENT
# ================================================================================
@app.route("/documents/<id>", methods=["GET"])
@token_required
def get_document(asking_staff, id):
    requested_document = Document.query.get(id)
    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type in [StaffType.ADMIN, StaffType.SECRETARY ]):
        return "{} type staff are not allowed to get medical documents ".format(asking_staff.type.value), 401
    if (requested_document is None):
        return "document_id doesn't match any patient", 400
    if(asking_staff.type == StaffType.NURSE and requested_document.type not in ALLOWED_DOC_TYPE_NURSE):
        return "NURSE are not allowed to see {} documents ".format(requested_document.type.value), 401
    if not is_a_child_node(asking_staff.node, requested_document.patient.node):
        return "this staff member is not allowed to see information about this patient (The patient is in a Care Unit you are not in charge of)", 401

    document_details = documentSchema.dump(requested_document).data
    return jsonify(document_details), 200


def check_document_integrity(new_document):
    return True, "Pas de probleme"


@app.route("/documents", methods=["POST"])
@token_required
def post_document(asking_staff):
    client_request = request.json
    load_result = documentSchema.load(client_request)

    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type not in [StaffType.DOCTOR, StaffType.NURSE]):
        return "{} type staff are not allowed to post documents ".format(asking_staff.type.value), 401

    if(len(load_result.errors) != 0):
        return jsonify(load_result.errors), 400

    new_document = load_result.data

    status, message = check_document_integrity(new_document)
    if(status == False):
        return message, 400

    if(new_document.status == DocumentStatus.VALIDATED):
        new_document.validation_ts = datetime.datetime.now()

    db.session.add(new_document)
    db.session.commit()
    response = documentSchema.dump(new_document).data
    return jsonify(response), 200


@app.route("/documents/<id>", methods=["PUT"])
@token_required
def update_document(asking_staff, id):
    client_request = request.json

    document_to_update = Document.query.get(id)

    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type not in [StaffType.DOCTOR, StaffType.NURSE]):
        return "{} type staff are not allowed to post documents ".format(asking_staff.type.value), 401

    if (document_to_update is None):
        return "document_id doesn't match any document in the database", 400

    if (document_to_update.status == DocumentStatus.VALIDATED):
        return "You can't update a VALIDATED document", 400

    load_result = documentSchema.load(client_request)
    if (len(load_result.errors) != 0):
        return jsonify(load_result.errors), 400

    new_document = load_result.data

    document_to_update.description = new_document.description if new_document.description is not None else document_to_update.description
    document_to_update.url_image = new_document.url_image if new_document.url_image is not None else document_to_update.url_image
    document_to_update.type = new_document.type if new_document.type is not None else document_to_update.type
    document_to_update.status = new_document.status if new_document.status is not None else document_to_update.status

    if (document_to_update.status == DocumentStatus.VALIDATED):
        document_to_update.validation_ts = datetime.datetime.now()

    status, message = check_document_integrity(document_to_update)
    if (status == False):
        db.session.roolback()
        return message, 400

    response = documentSchema.dump(document_to_update).data
    db.session.commit()
    return jsonify(response), 200


@app.route("/documents/draft", methods=["GET"])
@token_required
def get_draft(asking_staff):
    if (asking_staff is None):
        return "asking_staff missing ", 400

    requested_draft = Document.query.filter_by(author_id=asking_staff.id, status=DocumentStatus.IN_PROGRESS).all()
    if(requested_draft is None):
        return jsonify("This staff member doesn't have any pending draft "), 200

    document_details = documentsSchema.dump(requested_draft).data
    return jsonify(document_details), 200


# STAFF
# ================================================================================
@app.route("/staffs/asking_staff", methods=["GET"])
@token_required
def get_askings_taff(asking_staff):
    if (asking_staff is None):
        return "asking_staff missing ", 400
    staff_details = staffSchema.dump(asking_staff).data
    return jsonify(staff_details), 200


@app.route("/staffs/<id>", methods=["GET"])
@token_required
def get_staff(asking_staff, id):
    requested_staff = Staff.query.get(id)
    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type != StaffType.ADMIN):
        return "{} type staff are not allowed to get info about staff members".format(asking_staff.type.value), 401
    if (requested_staff is None):
        return "staff_id doesn't match any staff member", 400

    staff_details = staffSchema.dump(requested_staff).data
    return jsonify(staff_details), 200


@app.route("/staffs", methods=["GET"])
@token_required
def get_all_staff(asking_staff):
    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type != StaffType.ADMIN):
        return "{} type staff are not allowed to get info about staff members".format(asking_staff.type.value), 401

    staff_list = Staff.query.all()

    staff_list_details = staffsSchema.dump(staff_list).data
    return jsonify(staff_list_details), 200

def check_staff_integrity(new_staff):
    staff_node = Node.query.get(new_staff.node_id)
    if(staff_node is None):
        return False, "Can't find the node related to the staff node_id"

    if(new_staff.type == StaffType.ADMIN and staff_node.type != NodeType.ROOT):
        return False, "An Admin has to be assigned to a ROOT node"

    if (new_staff.type == StaffType.SECRETARY and staff_node.type != NodeType.HOSPITAL):
        return False, "A Secretary has to be assigned to a HOSPITAL node"

    if (new_staff.type in [StaffType.DOCTOR, StaffType.NURSE ] and staff_node.type not in [NodeType.DIVISION, NodeType.HOSPITAL_UNIT, NodeType.CARE_UNIT]):
        return False, "A medical staff can't be  assigned to a {} node".format(staff_node.type)

    return True, "Everything's fine"

@app.route("/staffs", methods=["POST"])
@token_required
def post_staff(asking_staff):
    client_request = request.json
    load_result = staffSchema.load(client_request)

    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type != StaffType.ADMIN):
        return "{} type staff are not allowed to post staff ".format(asking_staff.type.value), 401

    if(len(load_result.errors) != 0):
        return jsonify(load_result.errors), 400

    new_staff = load_result.data

    status, message = check_staff_integrity(new_staff)
    if(status == False):
        return message, 400

    new_staff.public_id = str(uuid.uuid4())
    hashed_password = generate_password_hash(new_staff.password, method='sha256')
    new_staff.password = hashed_password

    try:
        db.session.add(new_staff)
        db.session.commit()
    except exc.IntegrityError as e:
        db.session().rollback()
        return e.orig.pgerror, 400

    response = staffSchema.dump(new_staff).data
    return jsonify(response), 200


@app.route("/staffs/<id>", methods=["PUT"])
def update_staff(id):
    client_request = request.json

    staff_to_update = Staff.query.get(id)

    asking_staff = Staff.query.get(10)
    if (asking_staff is None):
        return "asking_staff missing ", 400
    if (asking_staff.type != StaffType.ADMIN):
        return "staff member that are {} are not allowed to update staff ".format(asking_staff.type.value), 401
    if (staff_to_update is None):
        return "staff_id doesn't match any staff member in the database", 400


    load_result = staffSchema.load(client_request)
    if (len(load_result.errors) != 0):
        return jsonify(load_result.errors), 400

    new_staff = load_result.data

    staff_to_update.firstName = new_staff.firstName if new_staff.firstName is not None else staff_to_update.firstName
    staff_to_update.lastName = new_staff.lastName if new_staff.lastName is not None else staff_to_update.lastName
    staff_to_update.node_id = new_staff.node_id if new_staff.node_id is not None else staff_to_update.node_id



    status, message = check_staff_integrity(staff_to_update)
    if (status == False):
        db.session.roolback()
        return message, 400

    response = staffSchema.dump(staff_to_update).data
    db.session.commit()
    return jsonify(response), 200

# ================================================================================
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


@app.route('/login')
def login():
    r = request
    print(request)
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    staff = Staff.query.filter_by(login=auth.username).first()

    if not staff:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if check_password_hash(staff.password, auth.password):
        token = jwt.encode({'public_id' : staff.public_id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])

        return jsonify({'token' : token.decode('UTF-8')})

    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

if __name__ == '__main__':
    app.run()