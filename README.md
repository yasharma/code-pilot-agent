# Agent-Based Code Modification Project

## Overview

This project demonstrates how to use OpenAI Agents to automatically modify code based on instructions and test feedback. It implements an automated code fixing workflow where an AI agent attempts to modify Python code to satisfy tests, with multiple retry attempts.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Install required packages:

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key
```

### Running the Project

To run the automated code fixing process:

```bash
python main.py
```

## Example Use Case

The default configuration modifies the `add` function in `calc.py` to perform subtraction instead of addition. This demonstrates how the system can adapt code based on instructions and test feedback.

## Customization

You can modify:

- `FILE_PATH` and `TEST_PATH` variables to work with different files
- `INSTRUCTION` to give the agent different modification instructions
- `MAX_RETRIES` to adjust how many attempts the agent makes
- The Agent definition in `agent.py` to change its behavior or instructions

## Dependencies

- [openai-agents](https://github.com/openai/openai-agents): For the Agent-based workflow
- pytest: For running tests 
- python-dotenv: For loading environment variables
