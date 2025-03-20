#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
from src.ai_integration import get_ai_provider, AIProvider
from src.providers.api_provider import APIProvider
from src.providers.ollama_provider import OllamaProvider

class TestAIIntegration(unittest.TestCase):
    """Test cases for the AI integration module."""
    
    def test_get_api_provider(self):
        """Test getting API provider."""
        config = {
            'model_provider': 'api',
            'api': {
                'api_endpoint': 'https://test-api.com',
                'model_name': 'test-model',
                'api_key': 'test-key'
            }
        }
        
        provider = get_ai_provider(config)
        
        self.assertIsInstance(provider, APIProvider)
        self.assertEqual(provider.api_endpoint, 'https://test-api.com')
        self.assertEqual(provider.model_name, 'test-model')
        self.assertEqual(provider.api_key, 'test-key')
    
    def test_get_ollama_provider(self):
        """Test getting Ollama provider."""
        config = {
            'model_provider': 'ollama',
            'ollama': {
                'base_url': 'http://test-ollama:11434',
                'ollama_model': 'test-ollama-model'
            }
        }
        
        provider = get_ai_provider(config)
        
        self.assertIsInstance(provider, OllamaProvider)
        self.assertEqual(provider.base_url, 'http://test-ollama:11434')
        self.assertEqual(provider.model_name, 'test-ollama-model')
    
    def test_get_provider_invalid(self):
        """Test getting provider with invalid type."""
        config = {
            'model_provider': 'invalid',
        }
        
        with self.assertRaises(ValueError):
            get_ai_provider(config)
    
    def test_prepare_prompt(self):
        """Test prompt preparation."""
        class TestProvider(AIProvider):
            def analyze_pr(self, diff_content, files):
                pass
        
        provider = TestProvider({})
        diff_content = "Test diff content"
        
        prompt = provider._prepare_prompt(diff_content)
        
        self.assertIn("You are a helpful code review assistant", prompt)
        self.assertIn("Test diff content", prompt)
    
    def test_parse_response(self):
        """Test response parsing."""
        class TestProvider(AIProvider):
            def analyze_pr(self, diff_content, files):
                pass
        
        provider = TestProvider({})
        response = """
        # Summary
        This is a test summary.
        
        # Suggestions
        1. First suggestion title
           First suggestion description.
        
        2. Second suggestion title
           Second suggestion description.
        """
        
        result = provider._parse_response(response)
        
        self.assertIn('summary', result)
        self.assertIn('suggestions', result)
        self.assertEqual(len(result['suggestions']), 2)
        self.assertEqual(result['suggestions'][0]['title'], 'First suggestion title')
        self.assertIn('First suggestion description', result['suggestions'][0]['description'])

if __name__ == '__main__':
    unittest.main() 