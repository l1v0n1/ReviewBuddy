#!/usr/bin/env python3
import os
import json
import logging
import base64
from github import Github
from github import GithubException

logger = logging.getLogger('reviewbuddy.github')

class GithubIntegration:
    """Class for interacting with GitHub API."""
    
    def __init__(self, token):
        """
        Initialize GitHub integration.
        
        Args:
            token (str): GitHub token
        """
        self.token = token
        self.github = Github(token)
        self.repo = None
        self.initialize_repo()
    
    def initialize_repo(self):
        """Initialize repository from GitHub context."""
        try:
            github_context = os.environ.get('GITHUB_CONTEXT')
            if github_context:
                context = json.loads(github_context)
                repo_name = context.get('repository', {}).get('full_name')
                if repo_name:
                    self.repo = self.github.get_repo(repo_name)
                    return
            
            # Fallback method using environment variables
            github_repository = os.environ.get('GITHUB_REPOSITORY')
            if github_repository:
                self.repo = self.github.get_repo(github_repository)
                return
                
            logger.error("Failed to determine repository from context")
        except Exception as e:
            logger.error(f"Error initializing repository: {str(e)}")
            raise
    
    def get_pr_number(self):
        """
        Get the pull request number from GitHub context.
        
        Returns:
            int: PR number or None
        """
        try:
            github_event_path = os.environ.get('GITHUB_EVENT_PATH')
            if github_event_path and os.path.exists(github_event_path):
                with open(github_event_path, 'r') as f:
                    event = json.load(f)
                    if 'pull_request' in event:
                        return event['pull_request']['number']
                    if 'issue' in event and 'pull_request' in event['issue']:
                        return event['issue']['number']
            
            # Fallback for direct environment variable
            pr_number = os.environ.get('GITHUB_PR_NUMBER')
            if pr_number:
                return int(pr_number)
                
            logger.warning("Could not determine PR number from context")
            return None
        except Exception as e:
            logger.error(f"Error getting PR number: {str(e)}")
            return None
    
    def get_pr_files(self, pr_number):
        """
        Get files and diff content from a PR.
        
        Args:
            pr_number (int): PR number
            
        Returns:
            tuple: (diff_content, files)
        """
        try:
            pr = self.repo.get_pull(pr_number)
            files = list(pr.get_files())
            
            # Get the diff content
            diff_content = ""
            for file in files:
                diff_content += f"File: {file.filename}\n"
                diff_content += f"Status: {file.status}\n"
                diff_content += f"Additions: {file.additions}, Deletions: {file.deletions}\n"
                diff_content += f"Patch:\n{file.patch if file.patch else 'No patch available'}\n\n"
            
            return diff_content, files
        except Exception as e:
            logger.error(f"Error getting PR files: {str(e)}")
            raise
    
    def get_file_content(self, file_path, ref=None):
        """
        Get content of a file from the repository.
        
        Args:
            file_path (str): Path to the file
            ref (str, optional): Reference (branch, commit) to get file from
            
        Returns:
            str: File content or None
        """
        try:
            contents = self.repo.get_contents(file_path, ref=ref)
            if isinstance(contents, list):
                logger.warning(f"{file_path} is a directory, not a file")
                return None
            
            content = base64.b64decode(contents.content).decode('utf-8')
            return content
        except GithubException as e:
            if e.status == 404:
                logger.warning(f"File {file_path} not found")
                return None
            else:
                logger.error(f"Error getting file content: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error getting file content: {str(e)}")
            raise
    
    def post_review_comment(self, pr_number, comment):
        """
        Post a review comment on a PR.
        
        Args:
            pr_number (int): PR number
            comment (str): Comment text
        """
        try:
            pr = self.repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            logger.info(f"Posted review comment on PR #{pr_number}")
        except Exception as e:
            logger.error(f"Error posting review comment: {str(e)}")
            raise
    
    def format_review_comment(self, static_analysis_results, ai_analysis):
        """
        Format the review comment from analysis results.
        
        Args:
            static_analysis_results (dict): Results from static analysis
            ai_analysis (dict): Results from AI analysis
            
        Returns:
            str: Formatted comment
        """
        comment = "## 🤖 ReviewBuddy Analysis\n\n"
        
        # Add AI summary
        comment += "### 🧠 AI Summary\n\n"
        comment += f"{ai_analysis.get('summary', 'No summary available')}\n\n"
        
        # Add AI suggestions
        suggestions = ai_analysis.get('suggestions', [])
        if suggestions:
            comment += "### 💡 Suggestions\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                comment += f"{i}. **{suggestion['title']}**\n"
                comment += f"   {suggestion['description']}\n\n"
        
        # Add static analysis results
        if static_analysis_results:
            comment += "### 🔍 Static Analysis\n\n"
            for tool, results in static_analysis_results.items():
                if results['issues']:
                    comment += f"#### {tool}\n\n"
                    for issue in results['issues']:
                        comment += f"- **{issue['severity']}**: {issue['message']} "
                        if issue.get('file') and issue.get('line'):
                            comment += f"[{issue['file']}:{issue['line']}]\n"
                        else:
                            comment += "\n"
                    comment += "\n"
        
        return comment 