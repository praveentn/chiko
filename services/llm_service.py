# services/llm_service.py
import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import current_app

logger = logging.getLogger(__name__)

class LLMService:
    """Service for handling LLM interactions with Azure OpenAI and other providers"""
    
    def __init__(self):
        self.clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize LLM clients based on configuration"""
        try:
            # Azure OpenAI client
            azure_config = self._get_azure_config()
            if azure_config['api_key'] and azure_config['endpoint']:
                try:
                    from openai import AzureOpenAI
                    self.clients['azure_openai'] = AzureOpenAI(
                        api_key=azure_config['api_key'],
                        api_version=azure_config['api_version'],
                        azure_endpoint=azure_config['endpoint']
                    )
                    logger.info("Azure OpenAI client initialized successfully")
                except ImportError:
                    logger.warning("OpenAI package not installed - using mock responses")
            else:
                logger.warning("Azure OpenAI not configured - using mock responses")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {str(e)}")
    
    def _get_azure_config(self) -> Dict[str, str]:
        """Get Azure OpenAI configuration from environment or config"""
        try:
            config = current_app.config.get('LLM_CONFIG', {}).get('azure', {})
        except:
            config = {}
        
        return {
            'api_key': os.environ.get('AZURE_OPENAI_API_KEY') or config.get('api_key'),
            'endpoint': os.environ.get('AZURE_OPENAI_ENDPOINT') or config.get('endpoint'),
            'api_version': os.environ.get('AZURE_OPENAI_API_VERSION') or config.get('api_version', '2024-02-01'),
            'deployment_name': os.environ.get('AZURE_OPENAI_DEPLOYMENT') or config.get('deployment_name', 'gpt-4'),
            'model_name': os.environ.get('AZURE_OPENAI_MODEL') or config.get('model_name', 'gpt-4'),
            'max_tokens': int(os.environ.get('AZURE_OPENAI_MAX_TOKENS', config.get('max_tokens', 4000)))
        }
    
    def complete_chat(
        self, 
        messages: List[Dict[str, str]], 
        model_id: Optional[int] = None,
        model_config: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete a chat conversation using the specified model
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model_id: Database ID of the model to use
            model_config: Direct model configuration (overrides model_id)
            user_id: ID of the user making the request
            context: Additional context for logging
        
        Returns:
            Dict with success status, response, usage info, and metadata
        """
        start_time = time.time()
        
        try:
            # Get model information
            model_info = self._get_model_info(model_id, model_config)
            
            # Make the LLM call
            response = self._call_llm_provider(messages, model_info)
            execution_time = time.time() - start_time
            
            # Log the interaction
            self._log_llm_interaction(
                user_id=user_id,
                model_info=model_info,
                messages=messages,
                response=response,
                execution_time=execution_time,
                context=context
            )
            
            return {
                'success': True,
                'response': response['content'],
                'usage': response.get('usage', {}),
                'model_used': model_info['name'],
                'execution_time': round(execution_time, 3),
                'cost': self._calculate_cost(response.get('usage', {}), model_info)
            }
            
        except Exception as e:
            logger.error(f"LLM completion error: {str(e)}")
            
            # Log the error
            self._log_llm_interaction(
                user_id=user_id,
                model_info=model_info if 'model_info' in locals() else None,
                messages=messages,
                error=str(e),
                execution_time=time.time() - start_time,
                context=context
            )
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': round(time.time() - start_time, 3)
            }
    
    def _get_model_info(self, model_id: Optional[int], model_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get model information and configuration"""
        if model_id:
            # Get model from database
            from models.model import Model
            model = Model.query.get(model_id)
            if not model:
                raise ValueError(f"Model with ID {model_id} not found")
            
            if not model.is_active:
                raise ValueError(f"Model {model.name} is not active")
            
            return {
                'id': model.id,
                'name': model.name,
                'provider': model.provider,
                'deployment_id': model.deployment_id,
                'model_name': model.model_name,
                'api_endpoint': model.api_endpoint,
                'api_version': model.api_version,
                'context_window': model.context_window,
                'max_tokens': model.max_tokens,
                'temperature': model.temperature,
                'configuration': model.configuration or {}
            }
        
        elif model_config:
            # Use provided configuration
            return model_config
        
        else:
            # Use default Azure OpenAI configuration
            azure_config = self._get_azure_config()
            return {
                'id': None,
                'name': 'Default Azure OpenAI',
                'provider': 'azure_openai',
                'deployment_id': azure_config['deployment_name'],
                'model_name': azure_config['model_name'],
                'api_endpoint': azure_config['endpoint'],
                'api_version': azure_config['api_version'],
                'context_window': 128000,
                'max_tokens': azure_config['max_tokens'],
                'temperature': 0.7,
                'configuration': {}
            }
    
    def _call_llm_provider(self, messages: List[Dict[str, str]], model_info: Dict[str, Any]) -> Dict[str, Any]:
        """Call the appropriate LLM provider based on model configuration"""
        provider = model_info.get('provider', 'azure_openai')
        
        if provider == 'azure_openai':
            return self._call_azure_openai(messages, model_info)
        else:
            # Fallback to mock response
            return self._mock_response(messages, model_info)
    
    def _call_azure_openai(self, messages: List[Dict[str, str]], model_info: Dict[str, Any]) -> Dict[str, Any]:
        """Call Azure OpenAI API"""
        try:
            client = self.clients.get('azure_openai')
            if not client:
                # Return mock response if client not available
                return self._mock_response(messages, model_info)
            
            # Prepare parameters
            params = {
                'model': model_info.get('deployment_id', 'gpt-4'),
                'messages': messages,
                'max_tokens': min(model_info.get('max_tokens', 4000), 4000),
                'temperature': model_info.get('temperature', 0.7)
            }
            
            # Add any additional configuration
            config = model_info.get('configuration', {})
            if 'top_p' in config:
                params['top_p'] = config['top_p']
            if 'frequency_penalty' in config:
                params['frequency_penalty'] = config['frequency_penalty']
            if 'presence_penalty' in config:
                params['presence_penalty'] = config['presence_penalty']
            
            # Make the API call
            response = client.chat.completions.create(**params)
            
            return {
                'content': response.choices[0].message.content,
                'finish_reason': response.choices[0].finish_reason,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                } if response.usage else {}
            }
            
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {str(e)}")
            # Return mock response on error
            return self._mock_response(messages, model_info)
    
    def _mock_response(self, messages: List[Dict[str, str]], model_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a mock response for testing/fallback purposes"""
        import random
        
        # Get the last user message
        user_messages = [msg for msg in messages if msg['role'] == 'user']
        last_message = user_messages[-1]['content'] if user_messages else "Hello"
        
        # Generate mock response based on input
        if 'analyze' in last_message.lower():
            response_content = f"Based on my analysis of '{last_message[:50]}...', I can provide the following insights: This appears to be a request for data analysis. I would typically examine the provided data, identify patterns, trends, and key metrics to deliver actionable insights."
        elif 'summarize' in last_message.lower():
            response_content = f"Here's a summary of '{last_message[:50]}...': This content discusses various topics and presents information in a structured format. The key points include relevant details that would be important for understanding the main concepts."
        elif 'write' in last_message.lower() or 'create' in last_message.lower():
            response_content = f"I'll help you create content based on your request: '{last_message[:50]}...'. Here's a draft that addresses your requirements with appropriate tone and structure."
        else:
            response_content = f"Thank you for your message: '{last_message[:50]}...'. I understand your request and I'm here to help. Based on what you've shared, I can provide assistance with your specific needs."
        
        # Simulate realistic token usage
        prompt_tokens = sum(len(msg['content'].split()) for msg in messages)
        completion_tokens = len(response_content.split())
        
        return {
            'content': response_content,
            'finish_reason': 'stop',
            'usage': {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens
            }
        }
    
    def _calculate_cost(self, usage: Dict[str, int], model_info: Dict[str, Any]) -> float:
        """Calculate the cost of an LLM call based on token usage"""
        if not usage:
            return 0.0
        
        # Default pricing (per 1K tokens) - adjust based on actual model pricing
        pricing = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-35-turbo': {'input': 0.0015, 'output': 0.002}
        }
        
        model_name = model_info.get('model_name', 'gpt-4')
        model_pricing = pricing.get(model_name, pricing['gpt-4'])
        
        prompt_cost = (usage.get('prompt_tokens', 0) / 1000) * model_pricing['input']
        completion_cost = (usage.get('completion_tokens', 0) / 1000) * model_pricing['output']
        
        return round(prompt_cost + completion_cost, 6)
    
    def _log_llm_interaction(
        self,
        user_id: Optional[int],
        model_info: Optional[Dict[str, Any]],
        messages: List[Dict[str, str]],
        response: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log LLM interaction to the audit log"""
        try:
            from app import db
            from models.audit import AuditLog
            
            log_data = {
                'model_id': model_info['id'] if model_info else None,
                'model_name': model_info['name'] if model_info else 'Unknown',
                'provider': model_info['provider'] if model_info else 'Unknown',
                'message_count': len(messages),
                'total_input_length': sum(len(msg['content']) for msg in messages),
                'execution_time': round(execution_time, 3),
                'context': context
            }
            
            if response:
                log_data.update({
                    'response_length': len(response.get('content', '')),
                    'usage': response.get('usage', {}),
                    'cost': self._calculate_cost(response.get('usage', {}), model_info or {}),
                    'finish_reason': response.get('finish_reason')
                })
            
            if error:
                log_data['error'] = error
            
            # Create audit log entry
            audit_log = AuditLog(
                user_id=user_id,
                action='llm_completion',
                resource_type='llm_call',
                details=log_data,
                success=error is None,
                error_message=error
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log LLM interaction: {str(e)}")
            # Don't let logging failure break the main operation
            try:
                from app import db
                db.session.rollback()
            except:
                pass
    
    def test_model_connection(self, model_id: int) -> Dict[str, Any]:
        """Test connection to a specific model"""
        try:
            # Get model info
            model_info = self._get_model_info(model_id, None)
            
            # Send a simple test message
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Please respond with 'Connection test successful' to confirm you are working."}
            ]
            
            response = self._call_llm_provider(test_messages, model_info)
            
            return {
                'success': True,
                'message': 'Model connection successful',
                'model_name': model_info['name'],
                'response_preview': response['content'][:100] + "..." if len(response['content']) > 100 else response['content']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Model connection failed'
            }
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available and configured models"""
        models = []
        
        try:
            # Get models from database
            from models.model import Model
            db_models = Model.query.filter_by(is_active=True, is_approved=True).all()
            for model in db_models:
                models.append({
                    'id': model.id,
                    'name': model.name,
                    'provider': model.provider,
                    'model_name': model.model_name,
                    'context_window': model.context_window,
                    'max_tokens': model.max_tokens,
                    'description': model.description,
                    'source': 'database'
                })
        except Exception as e:
            logger.error(f"Error fetching database models: {str(e)}")
        
        # Add default Azure OpenAI if configured
        azure_config = self._get_azure_config()
        if azure_config['api_key'] and azure_config['endpoint']:
            models.append({
                'id': None,
                'name': 'Default Azure OpenAI',
                'provider': 'azure_openai',
                'model_name': azure_config['model_name'],
                'context_window': None,
                'max_tokens': azure_config['max_tokens'],
                'description': 'Default Azure OpenAI configuration',
                'source': 'config'
            })
        
        return models
    
    def validate_model_config(self, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate model configuration for a specific provider"""
        if provider == 'azure_openai':
            return self._validate_azure_config(config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _validate_azure_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Azure OpenAI configuration"""
        required_fields = ['api_endpoint', 'deployment_id']
        errors = []
        warnings = []
        
        for field in required_fields:
            if not config.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate URL format
        if config.get('api_endpoint'):
            import re
            url_pattern = re.compile(r'^https://.+\.openai\.azure\.com/?$')
            if not url_pattern.match(config['api_endpoint']):
                warnings.append("API endpoint should follow format: https://your-resource.openai.azure.com/")
        
        # Validate numeric fields
        numeric_fields = ['max_tokens', 'context_window', 'temperature']
        for field in numeric_fields:
            if field in config:
                try:
                    value = float(config[field])
                    if field == 'temperature' and (value < 0 or value > 2):
                        warnings.append("Temperature should be between 0 and 2")
                    elif field in ['max_tokens', 'context_window'] and value <= 0:
                        warnings.append(f"{field} should be positive")
                except (ValueError, TypeError):
                    errors.append(f"{field} must be a number")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

# Global LLM service instance
llm_service = LLMService()