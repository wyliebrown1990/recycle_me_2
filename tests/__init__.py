# app/models.py
from . import db

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    items = db.relationship('Item', backref='location', lazy=True)

class Material(db.Model):
    __tablename__ = 'materials'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    items = db.relationship('Item', backref='material', lazy=True)

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)

class NonRecyclableItem(db.Model):
    __tablename__ = 'non_recyclable_items'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(255))
    material = db.Column(db.String(255))
    item_name = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class UnavailableLocation(db.Model):
    __tablename__ = 'unavailable_locations'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(255), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
