#!/usr/bin/env python3
import os
import tempfile
import subprocess
import logging
import json
import requests

logger = logging.getLogger('reviewbuddy.static_analysis')

def run_static_analysis(files, config):
    """
    Run static analysis on the provided files.
    
    Args:
        files (list): List of files from PR
        config (dict): Configuration dictionary
        
    Returns:
        dict: Results of static analysis by tool
    """
    if not config.get('static_analysis', {}).get('enabled', True):
        logger.info("Static analysis disabled in configuration")
        return {}
    
    results = {}
    
    # Group files by language
    files_by_language = group_files_by_language(files)
    
    # Get configured tools for each language
    tools_config = config.get('static_analysis', {}).get('tools', {})
    
    # Create a temporary directory to store files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download files to the temporary directory
        download_files(files, temp_dir)
        
        # Run analysis for each language and tool
        for language, file_list in files_by_language.items():
            tools = tools_config.get(language, [])
            for tool in tools:
                tool_results = run_tool(tool, language, file_list, temp_dir, config)
                if tool_results:
                    results[tool] = tool_results
    
    return results

def group_files_by_language(files):
    """
    Group files by language based on file extension.
    
    Args:
        files (list): List of files from PR
        
    Returns:
        dict: Files grouped by language
    """
    extensions = {
        'py': 'python',
        'js': 'javascript',
        'jsx': 'javascript',
        'ts': 'typescript',
        'tsx': 'typescript'
    }
    
    files_by_language = {}
    
    for file in files:
        filename = file.filename
        ext = filename.split('.')[-1].lower()
        language = extensions.get(ext)
        
        if language:
            if language not in files_by_language:
                files_by_language[language] = []
            files_by_language[language].append(filename)
    
    return files_by_language

def download_files(files, temp_dir):
    """
    Download files to a temporary directory.
    
    Args:
        files (list): List of files from PR
        temp_dir (str): Path to temporary directory
    """
    for file in files:
        if file.status != 'removed':
            # Create directories if they don't exist
            file_path = os.path.join(temp_dir, file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                if hasattr(file, 'raw_url') and file.raw_url:
                    try:
                        response = requests.get(file.raw_url, timeout=30)
                        response.raise_for_status()
                        f.write(response.text)
                    except (requests.RequestException, IOError) as e:
                        logger.error("Error downloading file %s: %s", file.filename, str(e))
                        continue
                elif hasattr(file, 'content') and file.content:
                    f.write(file.content)
                else:
                    logger.warning("No content available for file %s", file.filename)
                    continue

def run_tool(tool, language, file_list, temp_dir, config):
    """
    Run a specific static analysis tool on the provided files.
    
    Args:
        tool (str): Name of the tool to run
        language (str): Language of the files
        file_list (list): List of file paths
        temp_dir (str): Path to temporary directory
        config (dict): Configuration dictionary
        
    Returns:
        dict: Results of the tool
    """
    if not file_list:
        return None
    
    severity_threshold = config.get('static_analysis', {}).get('severity_threshold', 'warning')
    
    # Prepare result structure
    result = {
        'tool': tool,
        'language': language,
        'issues': []
    }
    
    try:
        if tool == 'pylint' and language == 'python':
            result['issues'] = run_pylint(file_list, temp_dir, severity_threshold)
        elif tool == 'flake8' and language == 'python':
            result['issues'] = run_flake8(file_list, temp_dir, severity_threshold)
        elif tool == 'eslint' and language in ['javascript', 'typescript']:
            result['issues'] = run_eslint(file_list, temp_dir, severity_threshold, language)
        else:
            logger.warning("Unsupported tool %s for language %s", tool, language)
            return None
    except subprocess.SubprocessError as e:
        logger.error("Error running %s on %s files: %s", tool, language, str(e))
        return None
    except Exception as e:  # Keep broad exception for now but improve logging
        logger.error("Unexpected error running %s on %s files: %s", tool, language, str(e))
        return None
    
    return result

def run_pylint(file_list, temp_dir, severity_threshold):
    """
    Run pylint on Python files.
    
    Args:
        file_list (list): List of file paths
        temp_dir (str): Path to temporary directory
        severity_threshold (str): Minimum severity level to report
        
    Returns:
        list: Pylint issues
    """
    issues = []
    
    try:
        # Prepare file paths
        file_paths = [os.path.join(temp_dir, file) for file in file_list]
        file_paths = [path for path in file_paths if os.path.exists(path)]
        
        if not file_paths:
            return issues
        
        # Run pylint
        cmd = ['pylint', '--output-format=json'] + file_paths
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Parse output
        if result.stdout:
            try:
                pylint_issues = json.loads(result.stdout)
                
                for issue in pylint_issues:
                    severity = map_pylint_severity(issue.get('type', ''))
                    if is_severity_included(severity, severity_threshold):
                        issues.append({
                            'file': issue.get('path', '').replace(temp_dir + '/', ''),
                            'line': issue.get('line', 0),
                            'message': issue.get('message', ''),
                            'severity': severity
                        })
            except json.JSONDecodeError:
                logger.error("Failed to parse pylint output")
    except Exception as e:
        logger.error(f"Error running pylint: {str(e)}")
    
    return issues

def run_flake8(file_list, temp_dir, severity_threshold):
    """
    Run flake8 on Python files.
    
    Args:
        file_list (list): List of file paths
        temp_dir (str): Path to temporary directory
        severity_threshold (str): Minimum severity level to report
        
    Returns:
        list: Flake8 issues
    """
    issues = []
    
    try:
        # Prepare file paths
        file_paths = [os.path.join(temp_dir, file) for file in file_list]
        file_paths = [path for path in file_paths if os.path.exists(path)]
        
        if not file_paths:
            return issues
        
        # Run flake8
        cmd = ['flake8', '--format=json'] + file_paths
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Parse output
        if result.stdout:
            try:
                flake8_issues = json.loads(result.stdout)
                
                for file_path, file_issues in flake8_issues.items():
                    for issue in file_issues:
                        # Flake8 doesn't provide severity, defaulting to warning
                        severity = 'warning'
                        if is_severity_included(severity, severity_threshold):
                            issues.append({
                                'file': file_path.replace(temp_dir + '/', ''),
                                'line': issue.get('line_number', 0),
                                'message': issue.get('text', ''),
                                'severity': severity
                            })
            except json.JSONDecodeError:
                logger.error("Failed to parse flake8 output")
    except Exception as e:
        logger.error(f"Error running flake8: {str(e)}")
    
    return issues

def run_eslint(file_list, temp_dir, severity_threshold, language):
    """
    Run eslint on JavaScript/TypeScript files.
    
    Args:
        file_list (list): List of file paths
        temp_dir (str): Path to temporary directory
        severity_threshold (str): Minimum severity level to report
        language (str): Language ('javascript' or 'typescript')
        
    Returns:
        list: ESLint issues
    """
    issues = []
    
    try:
        # Prepare file paths
        file_paths = [os.path.join(temp_dir, file) for file in file_list]
        file_paths = [path for path in file_paths if os.path.exists(path)]
        
        if not file_paths:
            return issues
        
        # Check if .eslintrc exists
        eslintrc_found = False
        for eslintrc_name in ['.eslintrc', '.eslintrc.js', '.eslintrc.json', '.eslintrc.yml']:
            if os.path.exists(os.path.join(temp_dir, eslintrc_name)):
                eslintrc_found = True
                break
        
        # Create a basic eslintrc if none exists
        if not eslintrc_found:
            eslintrc = {
                'env': {
                    'browser': True,
                    'es2021': True,
                    'node': True
                },
                'extends': [
                    'eslint:recommended',
                ],
                'parserOptions': {
                    'ecmaVersion': 'latest',
                    'sourceType': 'module'
                },
                'rules': {}
            }
            
            if language == 'typescript':
                eslintrc['parser'] = '@typescript-eslint/parser'
                eslintrc['extends'].append('plugin:@typescript-eslint/recommended')
                eslintrc['plugins'] = ['@typescript-eslint']
            
            with open(os.path.join(temp_dir, '.eslintrc.json'), 'w', encoding='utf-8') as f:
                json.dump(eslintrc, f)
        
        # Install necessary typescript parser if analyzing TypeScript
        if language == 'typescript':
            try:
                # Check if we need to initialize npm
                if not os.path.exists(os.path.join(temp_dir, 'package.json')):
                    subprocess.run(['npm', 'init', '-y'], cwd=temp_dir, capture_output=True, check=True)
                # Install typescript parser plugin
                subprocess.run(['npm', 'install', '--save-dev', '@typescript-eslint/parser', '@typescript-eslint/eslint-plugin'], 
                               cwd=temp_dir, capture_output=True, check=True)
            except subprocess.SubprocessError as e:
                logger.warning(f"Could not install TypeScript plugins: {str(e)}")
        
        # Run eslint with global installation
        cmd = ['eslint', '--format=json'] + file_paths
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Parse output
        if result.stdout:
            try:
                eslint_results = json.loads(result.stdout)
                
                for file_result in eslint_results:
                    file_path = file_result.get('filePath', '').replace(temp_dir + '/', '')
                    
                    for message in file_result.get('messages', []):
                        severity = map_eslint_severity(message.get('severity', 1))
                        if is_severity_included(severity, severity_threshold):
                            issues.append({
                                'file': file_path,
                                'line': message.get('line', 0),
                                'message': message.get('message', ''),
                                'severity': severity
                            })
            except json.JSONDecodeError:
                logger.error("Failed to parse eslint output")
    except Exception as e:
        logger.error(f"Error running eslint: {str(e)}")
    
    return issues

def map_pylint_severity(pylint_type):
    """Map pylint message type to severity."""
    mapping = {
        'fatal': 'error',
        'error': 'error',
        'warning': 'warning',
        'convention': 'info',
        'refactor': 'info',
        'info': 'info'
    }
    return mapping.get(pylint_type.lower(), 'info')

def map_eslint_severity(eslint_severity):
    """Map eslint severity number to string."""
    mapping = {
        0: 'info',
        1: 'warning',
        2: 'error'
    }
    return mapping.get(eslint_severity, 'info')

def is_severity_included(severity, threshold):
    """
    Check if the severity level should be included based on the threshold.
    
    Args:
        severity (str): Severity level of the issue
        threshold (str): Minimum severity level to include
        
    Returns:
        bool: True if the severity should be included
    """
    severity_levels = {
        'error': 3,
        'warning': 2,
        'info': 1
    }
    
    issue_level = severity_levels.get(severity.lower(), 0)
    threshold_level = severity_levels.get(threshold.lower(), 0)
    
    return issue_level >= threshold_level 