#!/usr/bin/env python3
import logging
from src.providers.api_provider import APIProvider
from src.providers.ollama_provider import OllamaProvider
import requests
import os

logger = logging.getLogger('reviewbuddy.ai_integration')

def get_ai_provider(config):
    """
    Get the appropriate AI provider based on configuration.
    
    Args:
        config (dict): Configuration dictionary
        
    Returns:
        AIProvider: The configured AI provider
    """
    provider_type = config.get('model_provider', 'api')
    
    # Try to use Ollama if configured
    if provider_type == 'ollama':
        try:
            # Check if Ollama is available
            base_url = config.get('ollama', {}).get('base_url', 'http://localhost:11434')
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            # If we got here, Ollama is available
            logger.info("Using Ollama provider")
            return OllamaProvider(config.get('ollama', {}))
        except (requests.RequestException, ConnectionError) as e:
            logger.warning("Ollama not available, falling back to API provider: %s", str(e))
            provider_type = 'api'
    
    # Use API provider as fallback or if configured
    if provider_type == 'api':
        # Check if API key is available
        api_key = config.get('api', {}).get('api_key')
        if not api_key:
            api_key = os.environ.get('REVIEWBUDDY_API_KEY')
            if api_key:
                config['api']['api_key'] = api_key
                logger.info("Using API key from environment variable")
            else:
                logger.warning("No API key found in config or environment, review may fail")
        
        logger.info("Using API provider")
        return APIProvider(config.get('api', {}))
    
    # If we got here, something is wrong with the configuration
    raise ValueError(f"Unsupported model provider: {provider_type}")

class AIProvider:
    """Base class for AI providers."""
    
    def __init__(self, config):
        """
        Initialize the AI provider.
        
        Args:
            config (dict): Provider-specific configuration
        """
        self.config = config
    
    def analyze_pr(self, diff_content, files):
        """
        Analyze a pull request using AI.
        
        Args:
            diff_content (str): Content of the PR diff
            files (list): List of files in the PR
            
        Returns:
            dict: Analysis results with summary and suggestions
        """
        raise NotImplementedError("Subclasses must implement analyze_pr method")
    
    def _prepare_prompt(self, diff_content):
        """
        Prepare the prompt for the AI model.
        
        Args:
            diff_content (str): Content of the PR diff
            
        Returns:
            str: Formatted prompt
        """
        prompt = "You are a helpful code review assistant. "
        prompt += "Please analyze the following code changes and provide: "
        prompt += "1. A brief summary of what the changes do. "
        prompt += "2. Any potential issues or improvements you spot. "
        prompt += "3. Specific suggestions for improving the code. "
        prompt += "4. Any security concerns or best practices that should be addressed. "
        prompt += "\n\nCode changes:\n\n"
        prompt += diff_content
        
        return prompt
    
    def _parse_response(self, response_text):
        """
        Parse the response from the AI model.
        
        Args:
            response_text (str): Response from the AI model
            
        Returns:
            dict: Parsed response with summary and suggestions
        """
        # Simple parsing, could be improved with more structured prompts
        lines = response_text.split('\n')
        
        summary = ""
        suggestions = []
        current_suggestion = None
        
        # Very basic parsing logic - could be improved
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for summary section
            if "summary" in line.lower() and not summary:
                summary_start = lines.index(line) + 1
                for i in range(summary_start, len(lines)):
                    if not lines[i].strip():
                        continue
                    if "issue" in lines[i].lower() or "suggestion" in lines[i].lower():
                        break
                    summary += lines[i] + " "
            
            # Look for suggestions/issues
            if line.startswith("- ") or line.startswith("* ") or (line[0].isdigit() and line[1] == '.'):
                if current_suggestion:
                    suggestions.append(current_suggestion)
                
                current_suggestion = {
                    "title": line.lstrip("- *0123456789. "),
                    "description": ""
                }
            elif current_suggestion and line:
                current_suggestion["description"] += line + " "
        
        # Add the last suggestion if exists
        if current_suggestion:
            suggestions.append(current_suggestion)
        
        return {
            "summary": summary.strip(),
            "suggestions": suggestions
        } 