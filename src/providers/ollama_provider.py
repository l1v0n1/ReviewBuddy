#!/usr/bin/env python3
import requests
import logging
from src.providers.base_provider import AIProvider

logger = logging.getLogger('reviewbuddy.providers.ollama')

class OllamaProvider(AIProvider):
    """Provider for local Ollama-based AI models."""
    
    def __init__(self, config):
        """
        Initialize the Ollama provider.
        
        Args:
            config (dict): Ollama-specific configuration
        """
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.model_name = config.get('ollama_model', 'llama3')
    
    def analyze_pr(self, diff_content, files):
        """
        Analyze a pull request using the Ollama provider.
        
        Args:
            diff_content (str): Content of the PR diff
            files (list): List of files in the PR
            
        Returns:
            dict: Analysis results with summary and suggestions
        """
        try:
            # Prepare the prompt
            prompt = self._prepare_prompt(diff_content)
            
            # Truncate if too long
            max_tokens = 8000  # Adjust based on model's context window
            if len(prompt) > max_tokens:
                logger.warning("Prompt too long (%d tokens), truncating", len(prompt))
                prompt = prompt[:max_tokens] + "...[truncated]"
            
            # Call Ollama
            response = self._call_ollama(prompt)
            
            # Parse the response
            return self._parse_response(response)
            
        except (requests.RequestException, ConnectionError) as e:
            logger.error("Error analyzing PR with Ollama provider: %s", str(e))
            return {
                "summary": "Error: Failed to analyze PR with Ollama provider: {}".format(str(e)),
                "suggestions": []
            }
        except Exception as e:
            logger.error("Unexpected error analyzing PR with Ollama provider: %s", str(e))
            return {
                "summary": "Error: Failed to analyze PR with Ollama provider: {}".format(str(e)),
                "suggestions": []
            }
    
    def _call_ollama(self, prompt):
        """
        Call Ollama with the given prompt.
        
        Args:
            prompt (str): Prompt for the AI model
            
        Returns:
            str: Response from Ollama
        """
        url = f"{self.base_url}/api/generate"
        
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": 0.5,
            "max_tokens": 2000,
            "stream": False
        }
        
        try:
            # First check if Ollama is available
            self._check_ollama_availability()
            
            # Make the API call
            response = requests.post(url, json=data, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            
            if 'response' in result:
                return result['response']
            else:
                logger.error("Unexpected response format from Ollama: %s", result)
                raise ValueError("Unexpected response format from Ollama")
                
        except requests.RequestException as e:
            logger.error("Error calling Ollama API: %s", str(e))
            raise
    
    def _check_ollama_availability(self):
        """
        Check if Ollama is available.
        
        Raises:
            ConnectionError: If Ollama is not available
        """
        try:
            # Try to list available models to check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            # Check if our model is available
            models = response.json().get('models', [])
            model_names = [model.get('name') for model in models]
            
            if self.model_name not in model_names:
                logger.warning("Model %s not found in Ollama. Available models: %s", 
                              self.model_name, model_names)
        except requests.RequestException as e:
            logger.error("Ollama not available at %s: %s", self.base_url, str(e))
            raise ConnectionError("Ollama not available at {}: {}".format(self.base_url, str(e))) from e 