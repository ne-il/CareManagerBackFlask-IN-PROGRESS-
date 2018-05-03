from app import db, Patient, Staff, Node,Document, NodeType, StaffType, DocumentType, DocumentStatus
from datetime import datetime
import random
import string


def add_root():
    root = Node("AP-HP", NodeType.ROOT, None)
    db.session.add(root)

def add_hopital():
    root = Node.query.filter_by(type=NodeType.ROOT).first()
    hopital = Node("HOPITAL SAINT ANTOINE", NodeType.HOSPITAL, root.id)
    db.session.add(hopital)

def add_division():
    hopital = Node.query.filter_by(type=NodeType.HOSPITAL).first()
    cardiologie = Node("CARDIOLOFIE", NodeType.DIVISION, hopital.id)
    db.session.add(cardiologie)

def add_patient():
    hopital = Node.query.filter_by(type=NodeType.HOSPITAL).first()

    usggastro = Node.query.filter_by(name="SA_US-GASTRO-1").first()
    usgcardio = Node.query.filter_by(name="SA_US-CARDIO-1").first()

    USNEURO = Node.query.filter_by(name="SL_US-NEURO-1").first()

    patient = Patient(firstName=generate_random_string(5),
                      lastName=generate_random_string(5),
                      address=generate_random_string(10),
                      birthdate=datetime.now(),
                      place_of_birth= "PARIS",
                      social_security_number= generate_random_string(10),
                      node_id=USNEURO.id,
                      )
    db.session.add(patient)

def add_staff():
    hopital = Node.query.filter_by(type=NodeType.HOSPITAL).first()
    staff = Staff(firstName=generate_random_string(5),
                  lastName=generate_random_string(5),
                  type=StaffType.SECRETARY,
                  node_id=hopital.id)
    db.session.add(staff)

def add_root_staff():
    root = Node.query.filter_by(type=NodeType.ROOT).first()
    staff = Staff(firstName="ROOTMAN",
                  lastName="ROOTMAN",
                  type=StaffType.DOCTOR,
                  node_id=root.id)
    db.session.add(staff)


def add_document():
    p = Patient.query.first()
    s = Staff.query.first()
    d = Document(type = DocumentType.OBSERVATION,
                 status = DocumentStatus.VALIDATED,
                 patient_id = p.id,
                 author_id = s.id)
    d.description = generate_random_string(5)
    d.url_image = generate_random_string(15)

    db.session.add(d)


def generate_random_string(n):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

def cleanAll():
    documents = Document.query.all()
    for d in documents:
        db.session.delete(d)

    patients = Patient.query.all()
    for p in patients:
        db.session.delete(p)

    staffs = Staff.query.all()
    for s in staffs:
        db.session.delete(s)

    nodes = Node.query.all()
    for n in nodes:
        db.session.delete(n)

    # n = Node.query.get(14)
    # db.session.delete(n)

    db.session.commit()
    return "OK"

def generation_arborescence():
    root = Node("AP-HP", NodeType.ROOT, None)

    hsa = Node("HOPITAL SAINT ANTOINE", NodeType.HOSPITAL, None)
    hsa.parent = root



    cardio = Node("SA_CARDIOLOGIE", NodeType.DIVISION, None)
    cardio.parent = hsa

    uh1hsa = Node("SA_UH-CARDIO-1", NodeType.HOSPITAL_UNIT, None)
    uh1hsa.parent = cardio

    us1hsa = Node("SA_US-CARDIO-1", NodeType.CARE_UNIT, None)
    us1hsa.parent = uh1hsa


    cardio = Node("SA_GASTRO-ENTEROLOGIE", NodeType.DIVISION, None)
    cardio.parent = hsa

    uh2hsa = Node("SA_UH-GASTRO-1", NodeType.HOSPITAL_UNIT, None)
    uh2hsa.parent = cardio

    us2hsa = Node("SA_US-GASTRO-1", NodeType.CARE_UNIT, None)
    us2hsa.parent = uh2hsa


    hsl = Node("HOPITAL SAINT LOUIS", NodeType.HOSPITAL, None)
    hsl.parent = root

    neuro = Node("SL_NEUROLOGIE", NodeType.DIVISION, None)
    neuro.parent = hsl

    uh1hsl = Node("SL_UH-NEURO-1", NodeType.HOSPITAL_UNIT, None)
    uh1hsl.parent = neuro

    us2hsl = Node("SL_US-NEURO-1", NodeType.CARE_UNIT, None)
    us2hsl.parent = uh1hsl


    db.session.add(root)
    db.session.commit()

# cleanAll()
# add_patient()
# generation_arborescence()
# add_root_staff()
# hopital = Node.query.filter_by(type=NodeType.HOSPITAL).first()
# print(hopital.staffs)
# root = Node.query.filter_by(type=NodeType.ROOT).first()
# hopital.parent = root
# print("Voici l'hopital: {} ".format(hopital))
# print("Arborescence de l'AP-HP: {} ".format(root))
# print("les parent de hopital: {} ".format(hopital.parent))

# print("Voici les patient de l'hopital: {} ".format(hopital.patients))
# print("Voici les staffs de l'hopital: {} ".format(hopital.staffs))

# p = Patient.query.get(7)
# print(p)

# s = Staff.query.get(3)
# print(s.documents)

# asking_staff = Staff.query.filter_by(firstName="ROOTMAN").first()
#
# saintantoine = Node.query.filter_by(name="HOPITAL SAINT LOUIS").first()
#
# asking_staff.node = saintantoine
#
# db.session.commit()

n = Node.query.get(59)

print(n.patients)