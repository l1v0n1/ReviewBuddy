# ReviewBuddy

🤖 An AI-powered code review assistant for GitHub pull requests.

## Overview

ReviewBuddy is a GitHub Action that automatically reviews pull requests using AI and static analysis tools. It provides insightful feedback on code changes to help maintain code quality and catch potential issues early in the development cycle.

## Features

- 🔄 **Automatic Trigger**: Runs on pull request events (opened, updated, reopened)
- 🔍 **Static Analysis**: Integrates tools like pylint, flake8, and ESLint to identify syntax errors and style issues
- 🧠 **AI-Powered Reviews**: Uses AI to analyze code changes and provide human-readable feedback
- 💬 **Detailed Comments**: Automatically posts a summary and suggestions as a PR comment
- ⚙️ **Configurable**: Customize behavior via a `.reviewbuddy.yml` configuration file
- 🌐 **Flexible AI Integration**: Choose between remote API models (like GPT-4o) or local models via Ollama

## Setup

### Basic Usage

Add this to your GitHub workflow file (e.g., `.github/workflows/reviewbuddy.yml`):

```yaml
name: ReviewBuddy Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Run ReviewBuddy
        uses: l1v0n1/reviewbuddy@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          # Optional: path to config file (default: '.reviewbuddy.yml')
          config_path: '.reviewbuddy.yml'
        env:
          # Required if using API model providers like OpenAI
          REVIEWBUDDY_API_KEY: ${{ secrets.REVIEWBUDDY_API_KEY }}
```

### Configuration

Create a `.reviewbuddy.yml` file in your repository:

```yaml
# AI Model Provider Configuration
model_provider: 'api'  # Options: 'api' or 'ollama'

# API Provider Configuration
api:
  api_endpoint: 'https://api.openai.com/v1'
  model_name: 'gpt-4o'
  # API key should be set via environment variable REVIEWBUDDY_API_KEY

# Ollama Provider Configuration
ollama:
  base_url: 'http://localhost:11434'
  ollama_model: 'llama3'

# Static Analysis Configuration
static_analysis:
  enabled: true
  tools:
    python: ['pylint', 'flake8']
    javascript: ['eslint']
    typescript: ['eslint']
  severity_threshold: 'warning'  # Options: 'info', 'warning', 'error'

# Comment Format Configuration
comment_format: 'markdown'
max_suggestions: 10
```

## Using Local Models with Ollama

To use local models, you'll need to:

1. Set up [Ollama](https://github.com/ollama/ollama) on your self-hosted runner
2. Configure ReviewBuddy to use Ollama:

```yaml
model_provider: 'ollama'
ollama:
  base_url: 'http://localhost:11434'  # Adjust if needed
  ollama_model: 'llama3'  # Or any other model you have pulled
```

## Environment Variables

- `REVIEWBUDDY_API_KEY`: API key for the chosen AI service (required when using `model_provider: 'api'`)

## Sample Review Output

ReviewBuddy generates comments like this:

```markdown
## 🤖 ReviewBuddy Analysis

### 🧠 AI Summary
This PR adds a new user authentication feature with email verification. It introduces a new UserAuth class and updates the login flow.

### 💡 Suggestions
1. **Potential security issue in password handling**
   The password is being stored in plaintext before hashing. Consider using a secure method to handle passwords.

2. **Missing input validation**
   Email validation is not comprehensive. Consider using a robust validation library.

### 🔍 Static Analysis

#### pylint
- **Warning**: Unused import 'datetime' [src/auth.py:3]
- **Error**: Missing function docstring [src/auth.py:45]
```

## Development

### Prerequisites

- Python 3.10+
- Docker (for building/testing)

### Local Setup

```bash
# Clone the repository
git clone https://github.com/l1v0n1/reviewbuddy.git
cd reviewbuddy

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

### Building Docker Image

```bash
docker build -t reviewbuddy .
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 