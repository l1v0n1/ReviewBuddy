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
        self.timeout = config.get('ai', {}).get('ollama', {}).get('timeout', 30)
    
    def analyze_pr(self, diff_content, files):
        """
        Analyze a pull request using Ollama.
        
        Args:
            diff_content (str): The diff content of the PR
            files (list): List of files in the PR
            
        Returns:
            dict: Analysis results
        """
        try:
            # Prepare the prompt
            prompt = self._prepare_prompt(diff_content, files)
            
            # Get response from Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            if 'response' not in result:
                raise ValueError("Invalid response from Ollama")
            
            # Parse the response into structured format
            return self._parse_response(result['response'])
            
        except requests.Timeout:
            logger.error("Timeout while communicating with Ollama")
            return {
                'summary': 'Analysis timed out. Please review changes manually.',
                'suggestions': [
                    'Consider running local static analysis tools.',
                    'Check for potential security issues.',
                    'Verify code style and best practices.'
                ]
            }
        except requests.RequestException as e:
            logger.error("Error communicating with Ollama: %s", str(e))
            return {
                'summary': 'Unable to analyze changes. Please review manually.',
                'suggestions': [
                    'Consider running local static analysis tools.',
                    'Check for potential security issues.',
                    'Verify code style and best practices.'
                ]
            }
        except Exception as e:  # Keep broad exception for now but improve logging
            logger.error("Unexpected error in Ollama analysis: %s", str(e))
            return {
                'summary': 'Analysis failed. Please review changes manually.',
                'suggestions': [
                    'Consider running local static analysis tools.',
                    'Check for potential security issues.',
                    'Verify code style and best practices.'
                ]
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

    def _prepare_prompt(self, diff_content, files):
        """
        Prepare the prompt for the AI model.
        
        Args:
            diff_content (str): The diff content of the PR
            files (list): List of files in the PR
            
        Returns:
            str: The prepared prompt
        """
        prompt = """You are a helpful code review assistant. Please analyze the following code changes and provide:
1. A summary of the changes
2. Potential issues or improvements
3. Security considerations
4. Performance implications

Here are the changes to review:

{diff}

Please provide your analysis in a clear, structured format."""

        return prompt.format(diff=diff_content) 