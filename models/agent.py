# models/agent.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from extensions import db                       # ← pull db from the shared extensions module

class Agent(db.Model):
    __tablename__ = 'agents'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuration
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    persona_id = Column(Integer, ForeignKey('personas.id'), nullable=False)
    
    # Execution settings
    execution_pattern = Column(String(100), default='sequential')  # sequential, parallel, hierarchical, event_loop
    max_turns = Column(Integer, default=10)
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    memory_type = Column(String(50), default='stateless')  # stateless, session, persistent
    
    # Tools
    tool_ids = Column(JSON, nullable=True)  # List of tool IDs
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    tags = Column(JSON, nullable=True)
    configuration = Column(JSON, nullable=True)
    
    # Relationships
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_by_user = relationship('User', back_populates='created_agents')
    model = relationship('Model')
    persona = relationship('Persona')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Executions
    executions = relationship('AgentExecution', back_populates='agent', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Agent {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'model_name': self.model.name if self.model else None,
            'persona_name': self.persona.name if self.persona else None,
            'execution_pattern': self.execution_pattern,
            'max_turns': self.max_turns,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'memory_type': self.memory_type,
            'tool_ids': self.tool_ids,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'tags': self.tags,
            'created_by': self.created_by_user.full_name if self.created_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AgentExecution(db.Model):
    __tablename__ = 'agent_executions'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    
    # Execution details
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    trace_data = Column(JSON, nullable=True)  # Full execution trace
    
    # Metrics
    status = Column(String(50), default='running')  # running, completed, failed, cancelled
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    execution_time = Column(Float, nullable=True)  # in seconds
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_trace = Column(Text, nullable=True)
    
    # Metadata
    executed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship('Agent', back_populates='executions')
    model = relationship('Model')
    
    def __repr__(self):
        return f'<AgentExecution {self.agent.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'agent_name': self.agent.name if self.agent else None,
            'status': self.status,
            'tokens_used': self.tokens_used,
            'cost': round(self.cost, 3) if self.cost else 0,
            'execution_time': round(self.execution_time, 3) if self.execution_time else None,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

