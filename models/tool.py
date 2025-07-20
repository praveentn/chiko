# models/tool.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from extensions import db                       # ← pull db from the shared extensions module

class Tool(db.Model):
    __tablename__ = 'tools'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Tool definition
    tool_type = Column(String(100), nullable=False)  # function, mcp_server, api
    function_schema = Column(JSON, nullable=False)  # JSON schema for arguments
    
    # Configuration
    endpoint_url = Column(String(500), nullable=True)
    authentication = Column(JSON, nullable=True)  # API keys, tokens
    
    # Metadata
    safety_tags = Column(JSON, nullable=True)
    rate_limit = Column(Integer, nullable=True)
    timeout = Column(Integer, default=30)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    
    # Health check
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(50), default='unknown')
    
    # Relationships
    mcp_server_id = Column(Integer, ForeignKey('mcp_servers.id'), nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Tool {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tool_type': self.tool_type,
            'function_schema': self.function_schema,
            'safety_tags': self.safety_tags,
            'rate_limit': self.rate_limit,
            'timeout': self.timeout,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'health_status': self.health_status,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class MCPServer(db.Model):
    __tablename__ = 'mcp_servers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Connection details
    server_url = Column(String(500), nullable=False)
    api_key = Column(String(255), nullable=True)
    version = Column(String(50), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_ping = Column(DateTime, nullable=True)
    status = Column(String(50), default='unknown')  # online, offline, error
    
    # Metadata
    capabilities = Column(JSON, nullable=True)
    
    # Relationships
    tools = relationship('Tool', cascade='all, delete-orphan')
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<MCPServer {self.name}>'

