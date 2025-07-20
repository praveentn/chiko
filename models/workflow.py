# models/workflow.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from extensions import db                       # ← pull db from the shared extensions module

class Workflow(db.Model):
    __tablename__ = 'workflows'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Workflow definition
    workflow_definition = Column(JSON, nullable=False)  # Node graph
    schedule_config = Column(JSON, nullable=True)  # CRON and triggers
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    tags = Column(JSON, nullable=True)
    
    # Relationships
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_by_user = relationship('User', back_populates='created_workflows')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Executions
    executions = relationship('WorkflowExecution', back_populates='workflow', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Workflow {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'workflow_definition': self.workflow_definition,
            'schedule_config': self.schedule_config,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'tags': self.tags,
            'created_by': self.created_by_user.full_name if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class WorkflowExecution(db.Model):
    __tablename__ = 'workflow_executions'
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey('workflows.id'), nullable=False)
    
    # Execution details
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    trace_data = Column(JSON, nullable=True)
    
    # Metrics
    status = Column(String(50), default='running')
    total_cost = Column(Float, default=0.0)
    execution_time = Column(Float, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Metadata
    executed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    trigger_type = Column(String(50), nullable=True)  # manual, scheduled, webhook
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflow = relationship('Workflow', back_populates='executions')
    
    def __repr__(self):
        return f'<WorkflowExecution {self.workflow.name}>'

