# models/persona.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from extensions import db                       # ← pull db from the shared extensions module

class Persona(db.Model):
    __tablename__ = 'personas'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Prompt configuration
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=True)
    
    # Input/Output schemas (Pydantic)
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    
    # Settings
    visibility = Column(String(50), default='private')  # private, team, public
    is_active = Column(Boolean, default=True, nullable=False)  # ← Added this column
    is_approved = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    tags = Column(JSON, nullable=True)
    variables = Column(JSON, nullable=True)  # Template variables
    
    # Relationships
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_by_user = relationship('User', back_populates='created_personas')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Versions
    versions = relationship('PersonaVersion', back_populates='persona', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Persona {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'user_prompt_template': self.user_prompt_template,
            'input_schema': self.input_schema,
            'output_schema': self.output_schema,
            'visibility': self.visibility,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'tags': self.tags,
            'variables': self.variables,
            'created_by': self.created_by_user.full_name if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PersonaVersion(db.Model):
    __tablename__ = 'persona_versions'
    
    id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey('personas.id'), nullable=False)
    version_number = Column(Integer, nullable=False)
    
    # Versioned content
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=True)
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    variables = Column(JSON, nullable=True)
    
    # Version metadata
    change_summary = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    persona = relationship('Persona', back_populates='versions')
    created_by_user = relationship('User')
    
    def __repr__(self):
        return f'<PersonaVersion {self.persona_id}-v{self.version_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'persona_id': self.persona_id,
            'version_number': self.version_number,
            'system_prompt': self.system_prompt,
            'user_prompt_template': self.user_prompt_template,
            'input_schema': self.input_schema,
            'output_schema': self.output_schema,
            'variables': self.variables,
            'change_summary': self.change_summary,
            'created_by': self.created_by_user.full_name if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }