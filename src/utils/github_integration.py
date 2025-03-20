#!/usr/bin/env python3
import os
import logging
from github import Github, GithubException

logger = logging.getLogger('reviewbuddy.github_integration')

class GithubIntegration:
    """GitHub integration for ReviewBuddy."""
    
    def __init__(self, token):
        """
        Initialize GitHub integration.
        
        Args:
            token (str): GitHub token
        """
        self.github = Github(token)
        self.repo = self._get_repo()
    
    def _get_repo(self):
        """Get the current repository."""
        try:
            repo_name = os.environ.get('GITHUB_REPOSITORY')
            if not repo_name:
                logger.error("GITHUB_REPOSITORY environment variable not set")
                raise ValueError("GITHUB_REPOSITORY environment variable not set")
            
            return self.github.get_repo(repo_name)
        except GithubException as e:
            logger.error("Failed to get repository: %s", str(e))
            raise
    
    def get_pr_number(self):
        """Get the current pull request number."""
        try:
            event_name = os.environ.get('GITHUB_EVENT_NAME')
            if event_name == 'pull_request':
                return int(os.environ.get('GITHUB_REF').split('/')[2])
            elif event_name == 'pull_request_target':
                return int(os.environ.get('GITHUB_REF').split('/')[2])
            else:
                logger.warning("Not running in a pull request context")
                return None
        except (ValueError, IndexError) as e:
            logger.error("Failed to get PR number: %s", str(e))
            return None
    
    def get_pr_files(self, pr_number):
        """
        Get the files and diff content from a pull request.
        
        Args:
            pr_number (int): Pull request number
            
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
        except GithubException as e:
            logger.error("Failed to get PR files: %s", str(e))
            raise
    
    def format_review_comment(self, static_analysis_results, ai_analysis):
        """
        Format the review comment from static analysis and AI results.
        
        Args:
            static_analysis_results (dict): Results from static analysis
            ai_analysis (dict): Results from AI analysis
            
        Returns:
            str: Formatted review comment
        """
        comment = []
        
        # Add AI analysis summary
        if ai_analysis.get('summary'):
            comment.append("## AI Analysis Summary")
            comment.append(ai_analysis['summary'])
            comment.append("")
        
        # Add AI suggestions
        if ai_analysis.get('suggestions'):
            comment.append("## AI Suggestions")
            for suggestion in ai_analysis['suggestions']:
                comment.append(f"- **{suggestion['title']}**")
                if suggestion.get('description'):
                    comment.append(f"  {suggestion['description']}")
            comment.append("")
        
        # Add static analysis results
        comment.append("## Static Analysis")
        if static_analysis_results and any(result.get('issues') for result in static_analysis_results.values()):
            for tool, result in static_analysis_results.items():
                if result.get('issues'):
                    comment.append(f"### {tool.title()}")
                    for issue in result['issues']:
                        comment.append(f"- **{issue['file']}:{issue['line']}** - {issue['message']}")
                        comment.append(f"  Severity: {issue['severity']}")
                    comment.append("")
        else:
            comment.append("No static analysis issues found.")
            comment.append("")
        
        return "\n".join(comment)
    
    def post_review_comment(self, pr_number, comment):
        """
        Post a review comment on a pull request.
        
        Args:
            pr_number (int): Pull request number
            comment (str): Review comment
        """
        try:
            pr = self.repo.get_pull(pr_number)
            pr.create_review(
                body=comment,
                event='COMMENT'
            )
            logger.info("Posted review comment on PR #%d", pr_number)
        except GithubException as e:
            logger.error("Failed to post review comment: %s", str(e))
            raise 