#!/usr/bin/env python3
import os
import yaml
import logging

logger = logging.getLogger('reviewbuddy.config')

DEFAULT_CONFIG = {
    'model_provider': 'api',
    'api': {
        'api_endpoint': 'https://api.openai.com/v1',
        'model_name': 'gpt-4o',
    },
    'ollama': {
        'base_url': 'http://localhost:11434',
        'ollama_model': 'llama3.2',
    },
    'static_analysis': {
        'enabled': True,
        'tools': {
            'python': ['pylint', 'flake8'],
            'javascript': ['eslint'],
            'typescript': ['eslint'],
        },
        'severity_threshold': 'warning',
    },
    'comment_format': 'markdown',
    'max_suggestions': 10,
}

def load_config(config_path, github):
    """
    Load configuration from the specified path or use defaults.
    
    Args:
        config_path (str): Path to the configuration file
        github (GithubIntegration): GitHub integration instance
        
    Returns:
        dict: Merged configuration with defaults
    """
    config = DEFAULT_CONFIG.copy()
    
    try:
        # Try to load the configuration file from the repository
        config_content = github.get_file_content(config_path)
        if config_content:
            user_config = yaml.safe_load(config_content)
            if user_config:
                # Deep merge the user configuration with defaults
                deep_merge(config, user_config)
    except Exception as e:
        logger.warning(f"Could not load configuration file '{config_path}': {str(e)}")
        logger.info("Using default configuration")
    
    # Check for environment variables that might override config
    api_key = os.environ.get('REVIEWBUDDY_API_KEY')
    if api_key and config['model_provider'] == 'api':
        config['api']['api_key'] = api_key
    
    # Validate configuration
    validate_config(config)
    
    return config

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
        logger.warning(f"Invalid model_provider '{config['model_provider']}'. Using 'api' as default.")
        config['model_provider'] = 'api'
    
    if config['model_provider'] == 'api' and 'api_key' not in config['api']:
        logger.warning("API key not found in configuration. Make sure to set REVIEWBUDDY_API_KEY environment variable.")
    
    return config 