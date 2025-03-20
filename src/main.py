#!/usr/bin/env python3
import os
import sys
import logging
from utils.config import load_config
from utils.github_integration import GithubIntegration
from static_analysis import run_static_analysis
from ai_integration import get_ai_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('reviewbuddy')

def main():
    """Main entry point for the ReviewBuddy action."""
    logger.info("Starting ReviewBuddy")
    
    # Get GitHub context
    github_token = os.environ.get('INPUT_GITHUB_TOKEN')
    config_path = os.environ.get('INPUT_CONFIG_PATH', '.reviewbuddy.yml')
    
    if not github_token:
        logger.error("GitHub token is required")
        sys.exit(1)
    
    try:
        # Initialize GitHub integration
        github = GithubIntegration(github_token)
        
        # Load configuration
        config = load_config(config_path, github)
        
        # Get pull request information
        pr_number = github.get_pr_number()
        if not pr_number:
            logger.error("Could not determine pull request number")
            sys.exit(1)
            
        # Get the PR diff and files
        diff_content, files = github.get_pr_files(pr_number)
        
        # Run static analysis
        static_analysis_results = run_static_analysis(files, config)
        
        # Get AI provider based on configuration
        ai_provider = get_ai_provider(config)
        
        # Use AI to analyze the PR
        ai_analysis = ai_provider.analyze_pr(diff_content, files)
        
        # Combine results
        review_comment = github.format_review_comment(static_analysis_results, ai_analysis)
        
        # Post review comment
        github.post_review_comment(pr_number, review_comment)
        
        logger.info("ReviewBuddy completed successfully")
        
    except Exception as e:
        logger.error(f"Error running ReviewBuddy: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 