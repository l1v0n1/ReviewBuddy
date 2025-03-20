#!/usr/bin/env python3
import os
import yaml
import logging
from github import GithubException

logger = logging.getLogger('reviewbuddy.config')

# Default configuration
DEFAULT_CONFIG = {
    'model_provider': 'api',
    'api': {
        'model_name': 'gpt-4',
        'api_key': os.environ.get('REVIEWBUDDY_API_KEY'),
        'api_url': 'https://api.openai.com/v1/chat/completions'
    },
    'ollama': {
        'base_url': 'http://localhost:11434',
        'ollama_model': 'llama3'
    },
    'static_analysis': {
        'enabled': True,
        'severity_threshold': 'warning',
        'tools': {
            'python': ['pylint', 'flake8'],
            'javascript': ['eslint'],
            'typescript': ['eslint']
        }
    }
}

def load_config(config_path, github):
    """
    Load configuration from file or repository.
    
    Args:
        config_path (str): Path to config file
        github (GithubIntegration): GitHub integration instance
        
    Returns:
        dict: Configuration dictionary
    """
    try:
        # Try to load from file first
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info("Loaded configuration from %s", config_path)
                return config
        
        # Try to load from repository
        try:
            content = github.repo.get_contents(config_path)
            if isinstance(content, list):
                logger.error("%s is a directory, not a file", config_path)
                raise ValueError("{} is a directory, not a file".format(config_path))
            
            config = yaml.safe_load(content.decoded_content.decode('utf-8'))
            logger.info("Loaded configuration from repository")
            return config
        except GithubException as e:
            if e.status == 404:
                logger.warning("Configuration file %s not found, using defaults", config_path)
                return get_default_config()
            else:
                logger.error("Failed to load configuration from repository: %s", str(e))
                raise
                
    except yaml.YAMLError as e:
        logger.error("Failed to parse configuration file: %s", str(e))
        raise ValueError("Failed to parse configuration file: {}".format(str(e))) from e
    except Exception as e:  # Keep broad exception for now but improve logging
        logger.error("Unexpected error loading configuration: %s", str(e))
        raise

def get_default_config():
    """
    Get default configuration.
    
    Returns:
        dict: Default configuration
    """
    return DEFAULT_CONFIG.copy()

def deep_merge(target, source):
    """
    Deep merge two dictionaries. Keys from source override keys from target
    if they have the same name. If both values are dictionaries, they are
    merged recursively.
    
    Args:
        target (dict): Target dictionary to merge into
        source (dict): Source dictionary to merge from
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value)
        else:
            target[key] = value

def validate_config(config):
    """
    Validate the configuration to ensure required fields are present.
    
    Args:
        config (dict): Configuration dictionary
    
    Raises:
        ValueError: If configuration is invalid
    """
    if config['model_provider'] not in ['api', 'ollama']:
        logger.warning("Invalid model_provider '%s'. Using 'api' as default.", config['model_provider'])
        config['model_provider'] = 'api'
    
    if config['model_provider'] == 'api' and 'api_key' not in config['api']:
        logger.warning("API key not found in configuration. Make sure to set REVIEWBUDDY_API_KEY environment variable.")
    
    return config 