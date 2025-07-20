# models/model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from extensions import db                       # ← pull db from the shared extensions module

class Model(db.Model):
    __tablename__ = 'models'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)  # e.g., 'azure_openai', 'openai', 'anthropic'
    deployment_id = Column(String(255), nullable=True)
    model_name = Column(String(255), nullable=False)  # e.g., 'gpt-4', 'claude-3'
    
    # Configuration
    api_endpoint = Column(String(500), nullable=True)
    api_version = Column(String(50), nullable=True)
    context_window = Column(Integer, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(Float, default=0.1)
    
    # Pricing
    input_cost_per_token = Column(Float, nullable=True)
    output_cost_per_token = Column(Float, nullable=True)
    
    # Status and approval
    is_active = Column(Boolean, default=True, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    approval_stage = Column(String(50), default='draft')  # draft, test, prod
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    configuration = Column(JSON, nullable=True)
    
    # Relationships
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_by_user = relationship('User', back_populates='created_models')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Versions
    versions = relationship('ModelVersion', back_populates='model', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Model {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'model_name': self.model_name,
            'context_window': self.context_window,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'approval_stage': self.approval_stage,
            'description': self.description,
            'tags': self.tags,
            'created_by': self.created_by_user.full_name if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ModelVersion(db.Model):
    __tablename__ = 'model_versions'
    
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    version = Column(String(50), nullable=False)
    
    # Configuration snapshot
    configuration = Column(JSON, nullable=False)
    changelog = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    model = relationship('Model', back_populates='versions')
    
    def __repr__(self):
        return f'<ModelVersion {self.model.name} v{self.version}>'

