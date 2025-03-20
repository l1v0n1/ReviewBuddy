#!/usr/bin/env python3
import os
import requests
import logging
import json
from src.ai_integration import AIProvider

logger = logging.getLogger('reviewbuddy.providers.api')

class APIProvider(AIProvider):
    """Provider for remote API-based AI models."""
    
    def __init__(self, config):
        """
        Initialize the API provider.
        
        Args:
            config (dict): API-specific configuration
        """
        super().__init__(config)
        self.api_endpoint = config.get('api_endpoint', 'https://api.openai.com/v1')
        self.model_name = config.get('model_name', 'gpt-4o')
        
        # Get API key from config or environment
        self.api_key = config.get('api_key')
        if not self.api_key:
            self.api_key = os.environ.get('REVIEWBUDDY_API_KEY')
            if not self.api_key:
                logger.warning("No API key provided for API provider")
    
    def analyze_pr(self, diff_content, files):
        """
        Analyze a pull request using the API provider.
        
        Args:
            diff_content (str): Content of the PR diff
            files (list): List of files in the PR
            
        Returns:
            dict: Analysis results with summary and suggestions
        """
        if not self.api_key:
            logger.error("Cannot analyze PR: No API key provided")
            return {
                "summary": "Error: No API key provided for the AI model.",
                "suggestions": []
            }
        
        try:
            # Prepare the prompt
            prompt = self._prepare_prompt(diff_content)
            
            # Truncate if too long
            max_tokens = 8000  # Adjust based on model's context window
            if len(prompt) > max_tokens:
                logger.warning(f"Prompt too long ({len(prompt)} tokens), truncating")
                prompt = prompt[:max_tokens] + "...[truncated]"
            
            # Call the API
            response = self._call_api(prompt)
            
            # Parse the response
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing PR with API provider: {str(e)}")
            return {
                "summary": f"Error: Failed to analyze PR with API provider: {str(e)}",
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
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful code review assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 2000
        }
        
        # Determine the appropriate endpoint
        if 'openai.com' in self.api_endpoint:
            endpoint = f"{self.api_endpoint}/chat/completions"
        else:
            # For other API providers, adjust as needed
            endpoint = self.api_endpoint
        
        response = requests.post(endpoint, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract content based on API response format
        try:
            # OpenAI format
            if 'choices' in result and len(result['choices']) > 0:
                if 'message' in result['choices'][0]:
                    return result['choices'][0]['message']['content']
                elif 'text' in result['choices'][0]:
                    return result['choices'][0]['text']
        except Exception as e:
            logger.error(f"Error parsing API response: {str(e)}")
            raise
        
        # If we couldn't parse the response
        logger.error(f"Unexpected API response format: {json.dumps(result)[:100]}...")
        raise ValueError("Unexpected API response format") 