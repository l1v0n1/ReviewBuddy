#!/usr/bin/env python3
import unittest
import os
from unittest.mock import MagicMock, patch
import yaml
from src.utils.config import load_config, deep_merge, validate_config, DEFAULT_CONFIG

class TestConfig(unittest.TestCase):
    """Test cases for the configuration module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.github_mock = MagicMock()
        
    def test_default_config(self):
        """Test that default config is returned when no config file exists."""
        self.github_mock.get_file_content.return_value = None
        
        config = load_config('.nonexistent_file.yml', self.github_mock)
        
        self.assertEqual(config['model_provider'], 'api')
        self.assertEqual(config['api']['model_name'], 'gpt-4o')
        self.assertTrue(config['static_analysis']['enabled'])
        
    def test_load_custom_config(self):
        """Test loading a custom configuration file."""
        custom_config_content = """
        model_provider: 'ollama'
        ollama:
          ollama_model: 'custom_model'
        static_analysis:
          severity_threshold: 'error'
        """
        
        self.github_mock.get_file_content.return_value = custom_config_content
        
        with patch('yaml.safe_load', return_value={
            'model_provider': 'ollama',
            'ollama': {
                'ollama_model': 'custom_model'
            },
            'static_analysis': {
                'severity_threshold': 'error'
            }
        }):
            config = load_config('.reviewbuddy.yml', self.github_mock)
            
            self.assertEqual(config['model_provider'], 'ollama')
            self.assertEqual(config['ollama']['ollama_model'], 'custom_model')
            self.assertEqual(config['static_analysis']['severity_threshold'], 'error')
            # Default values should still be present
            self.assertTrue(config['static_analysis']['enabled'])
            
    def test_deep_merge(self):
        """Test the deep merge function."""
        target = {
            'a': 1,
            'b': {
                'c': 2,
                'd': 3
            }
        }
        
        source = {
            'b': {
                'c': 4,
                'e': 5
            },
            'f': 6
        }
        
        expected = {
            'a': 1,
            'b': {
                'c': 4,
                'd': 3,
                'e': 5
            },
            'f': 6
        }
        
        deep_merge(target, source)
        self.assertEqual(target, expected)
        
    def test_api_key_from_env(self):
        """Test that API key is loaded from environment variable."""
        self.github_mock.get_file_content.return_value = None
        
        with patch.dict(os.environ, {'REVIEWBUDDY_API_KEY': 'test_api_key'}):
            config = load_config('.reviewbuddy.yml', self.github_mock)
            self.assertEqual(config['api']['api_key'], 'test_api_key')
            
    def test_validate_config_invalid_provider(self):
        """Test validation with invalid provider."""
        config = DEFAULT_CONFIG.copy()
        config['model_provider'] = 'invalid'
        
        with patch('logging.Logger.warning') as mock_warning:
            validated_config = validate_config(config)
            self.assertEqual(validated_config['model_provider'], 'api')
            mock_warning.assert_called()
            
    def test_validate_config_missing_api_key(self):
        """Test validation with missing API key."""
        config = DEFAULT_CONFIG.copy()
        config['model_provider'] = 'api'
        if 'api_key' in config['api']:
            del config['api']['api_key']
        
        with patch('logging.Logger.warning') as mock_warning:
            validate_config(config)
            mock_warning.assert_called()

if __name__ == '__main__':
    unittest.main() 