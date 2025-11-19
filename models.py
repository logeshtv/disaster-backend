"""
Database models for disaster relief management system
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Hub(Base):
    """Relief hubs/centers that store and distribute supplies"""
    __tablename__ = 'hubs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    location_name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    inventory = Column(JSON, default=dict)  # {item_name: quantity}
    contact = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location_name': self.location_name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'inventory': self.inventory or {},
            'contact': self.contact,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Donation(Base):
    """Donations made by donors"""
    __tablename__ = 'donations'
    
    id = Column(Integer, primary_key=True)
    donor_name = Column(String(255), nullable=False)
    donor_email = Column(String(255))
    donor_phone = Column(String(50))
    items = Column(JSON, nullable=False)  # {item_name: quantity}
    amount = Column(Float, default=0.0)  # Monetary donation
    allocated_status = Column(String(50), default='pending')  # pending, allocated, fulfilled
    allocated_to_victim_id = Column(Integer, nullable=True)
    allocated_to_hub_id = Column(Integer, nullable=True)
    notes = Column(Text)
    # Optional payment/bank/QR information (stored as JSON). Example: { type: 'bank', account_name:..., account_number:..., qr: 'data' }
    payment_info = Column(JSON, default=dict)
    # Tracking: current status and history for delivery (admin updates)
    tracking_status = Column(String(50), default='pending')
    tracking_history = Column(JSON, default=list)  # list of {status, note, timestamp, hub_id}
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'donor_name': self.donor_name,
            'donor_email': self.donor_email,
            'donor_phone': self.donor_phone,
            'items': self.items or {},
            'amount': self.amount,
            'allocated_status': self.allocated_status,
            'allocated_to_victim_id': self.allocated_to_victim_id,
            'allocated_to_hub_id': self.allocated_to_hub_id,
            'notes': self.notes,
            'payment_info': self.payment_info or {},
            'tracking_status': self.tracking_status,
            'tracking_history': self.tracking_history or [],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class VictimRequest(Base):
    """Requests from victims/affected people"""
    __tablename__ = 'victim_requests'
    
    id = Column(Integer, primary_key=True)
    victim_name = Column(String(255), nullable=False)
    victim_phone = Column(String(50))
    location_name = Column(String(255), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    requested_items = Column(JSON, nullable=False)  # {item_name: quantity}
    urgency = Column(String(20), default='medium')  # low, medium, high, critical
    fulfilled_status = Column(String(50), default='pending')  # pending, in_progress, fulfilled
    fulfilled_by_hub_id = Column(Integer, nullable=True)
    fulfilled_by_donation_id = Column(Integer, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'victim_name': self.victim_name,
            'victim_phone': self.victim_phone,
            'location_name': self.location_name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'requested_items': self.requested_items or {},
            'urgency': self.urgency,
            'fulfilled_status': self.fulfilled_status,
            'fulfilled_by_hub_id': self.fulfilled_by_hub_id,
            'fulfilled_by_donation_id': self.fulfilled_by_donation_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DisasterEvent(Base):
    """Detected disaster events from tweets"""
    __tablename__ = 'disaster_events'
    
    id = Column(Integer, primary_key=True)
    tweet_text = Column(Text, nullable=False)
    detected_location = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    disaster_type = Column(String(100))  # earthquake, flood, hurricane, etc.
    severity = Column(String(20))  # low, medium, high, critical
    nearby_hubs_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'tweet_text': self.tweet_text,
            'detected_location': self.detected_location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'disaster_type': self.disaster_type,
            'severity': self.severity,
            'nearby_hubs_count': self.nearby_hubs_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Database engine and session
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///disaster_relief.db')
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let the caller handle it
