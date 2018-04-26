import os
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import Patient, Document, Result



@app.route('/')
def hello():
    # return "Hello World!"
    p = Patient()
    d1 = Document()
    d2 = Document()
    p.documents.append(d1)
    p.documents.append(d2)

    s = str(p.documents)
    return s

    return str(os.environ['APP_SETTINGS'])

@app.route('/<name>')
def hello_name(name):
    return "Hello  {}!".format(name)


if __name__ == '__main__':
    app.run()

