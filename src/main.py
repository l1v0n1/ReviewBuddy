#!/usr/bin/env python3
import os
import sys
import logging
from src.utils.config import load_config
from src.utils.github_integration import GithubIntegration
from src.static_analysis import run_static_analysis
from src.ai_integration import get_ai_provider

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
    github_token = os.environ.get('INPUT_GITHUB_TOKEN') or os.environ.get('GITHUB_TOKEN')
    config_path = os.environ.get('INPUT_CONFIG_PATH', '.reviewbuddy.yml')
    
    if not github_token:
        logger.error("GitHub token is required. Set INPUT_GITHUB_TOKEN or GITHUB_TOKEN environment variable.")
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
        
        # Run static analysis (continue even if it fails)
        static_analysis_results = []
        try:
            static_analysis_results = run_static_analysis(files, config)
        except Exception as e:
            logger.error("Static analysis failed: %s", str(e))
        
        # Get AI provider based on configuration (with fallback)
        ai_analysis = {
            "summary": "⚠️ **This is an automated review.** ⚠️\n\nReviewBuddy couldn't connect to AI services. This is a basic analysis without AI assistance.",
            "suggestions": [
                {
                    'title': 'Configure AI providers',
                    'description': (
                        "To get better reviews, either:\n"
                        "1. Start Ollama locally (`ollama serve` and `ollama pull llama3`)\n"
                        "2. Or set an API key via the REVIEWBUDDY_API_KEY environment variable"
                    )
                },
                {
                    'title': 'Review your code manually',
                    'description': (
                        "Without AI assistance, please consider:\n"
                        "- Code style consistency\n"
                        "- Error handling\n"
                        "- Security implications\n"
                        "- Test coverage"
                    )
                }
            ]
        }
        
        try:
            ai_provider = get_ai_provider(config)
            ai_analysis = ai_provider.analyze_pr(diff_content, files)
        except Exception as e:
            logger.error("AI analysis failed: %s", str(e))
        
        # Combine results
        review_comment = github.format_review_comment(static_analysis_results, ai_analysis)
        
        # Post review comment
        github.post_review_comment(pr_number, review_comment)
        
        logger.info("ReviewBuddy completed successfully")
        
    except (ValueError, KeyError, ImportError) as e:
        logger.error("Error running ReviewBuddy: %s", str(e))
        sys.exit(1)
    except (OSError, IOError) as e:
        logger.error("File system error: %s", str(e))
        sys.exit(1)
    except Exception as e:  # Keep broad exception for now but improve logging
        logger.error("Unexpected error running ReviewBuddy: %s", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main() 