#!/usr/bin/env python3
import requests
import logging
from src.providers.base_provider import AIProvider

logger = logging.getLogger('reviewbuddy.providers.api')

class APIProvider(AIProvider):
    """Provider for API-based AI models."""
    
    def __init__(self, config):
        """
        Initialize the API provider.
        
        Args:
            config (dict): API-specific configuration
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.api_url = config.get('api_url')
        self.model_name = config.get('model_name', 'gpt-4')
        
        if not self.api_key or not self.api_url:
            raise ValueError("API key and URL are required for API provider")
    
    def analyze_pr(self, diff_content, files):
        """
        Analyze a pull request using the API provider.
        
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
            
            # Call API
            response = self._call_api(prompt)
            
            # Parse the response
            return self._parse_response(response)
            
        except (requests.RequestException, ConnectionError) as e:
            logger.error("Error analyzing PR with API provider: %s", str(e))
            return {
                "summary": "Error: Failed to analyze PR with API provider: {}".format(str(e)),
                "suggestions": []
            }
        except Exception as e:
            logger.error("Unexpected error analyzing PR with API provider: %s", str(e))
            return {
                "summary": "Error: Failed to analyze PR with API provider: {}".format(str(e)),
                "suggestions": []
            }
    
    def _call_api(self, prompt):
        """
        Call the API with the given prompt.
        
        Args:
            prompt (str): Prompt for the AI model
            
        Returns:
            str: Response from the API
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a code review assistant. Analyze the provided code changes and provide constructive feedback."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(self.api_url, json=data, headers=headers, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and result['choices']:
                return result['choices'][0]['message']['content']
            else:
                logger.error("Unexpected response format from API: %s", result)
                raise ValueError("Unexpected response format from API")
                
        except requests.RequestException as e:
            logger.error("Error calling API: %s", str(e))
            raise 