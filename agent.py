from agents import Agent, Runner

# Template strings for common prompt components
PYTHON_CODE_ONLY = """
Return ONLY the Python code without any explanations or markdown formatting.
Do not include any text like "Here's the modified code:" or explanations.
Return ONLY the raw Python code that should be saved directly to the file.
"""

# Create an agent for code modification
code_agent = Agent(
    name="Code Modifier",
    instructions=f"You are an expert at modifying Python code based on instructions. {PYTHON_CODE_ONLY}",
)

test_agent = Agent(
    name="Test Writer",
    instructions=f"You are an expert at writing test cases for Python code. {PYTHON_CODE_ONLY}",
)

analysis_agent = Agent(
    name="Code Analyzer",
    instructions="You analyze code to determine if specific functionality already exists. Respond with only 'yes' or 'no' followed by a brief explanation."
)

file_agent = Agent(
    name="File Planner",
    instructions="You analyze instructions and determine what files need to be created or modified. Provide concise and specific responses."
)


def strip_markdown(response):
    """Helper function to strip markdown code block formatting."""
    if response.startswith("```python"):
        response = response.replace("```python", "", 1)
    if response.startswith("```"):
        response = response.replace("```", "", 1)
    if response.endswith("```"):
        response = response[:-3]
    return response.strip()


async def ask_agent(prompt, agent=code_agent):
    result = await Runner.run(agent, input=prompt)
    return strip_markdown(result.final_output.strip())


async def check_functionality_exists(code, instruction):
    prompt = f"""Analyze this Python code and determine if it already implements the functionality described in the instruction.
    
Original code:
```python
{code}
```

Instruction:
{instruction}

Does the code already contain a function that implements this specific functionality?
Respond with ONLY 'yes' or 'no' followed by a very brief explanation.
"""
    response = await Runner.run(analysis_agent, input=prompt)
    return response.final_output.strip().lower().startswith("yes")


async def determine_file_action(instruction, existing_files):
    """Determine if we need to create a new file or modify an existing one."""
    prompt = f"""Based on the following instruction, determine if we should:
1. Create a new file
2. Modify an existing file from the list

Instruction:
{instruction}

Existing files:
{', '.join(existing_files)}

First, analyze if the instruction implies creating a completely new module/functionality that would be better as a separate file,
or if it's enhancing existing functionality.

Respond in the format:
ACTION: [CREATE or MODIFY]
FILE: [filename if modifying, or suggested new filename if creating]
REASON: [brief explanation]

If creating a new file, suggest an appropriate filename with proper extension based on the functionality described.
"""
    response = await Runner.run(file_agent, input=prompt)
    result = response.final_output.strip()
    
    # Parse the response
    action = None
    filename = None
    reason = None
    
    for line in result.split('\n'):
        if line.startswith('ACTION:'):
            action = line.replace('ACTION:', '').strip().upper()
        elif line.startswith('FILE:'):
            filename = line.replace('FILE:', '').strip()
        elif line.startswith('REASON:'):
            reason = line.replace('REASON:', '').strip()
    
    return {
        'action': action,
        'filename': filename,
        'reason': reason
    }


async def generate_new_file(instruction, filename):
    """Generate content for a new file."""
    prompt = f"""Create a new Python file based on this instruction:

Instruction:
{instruction}

Filename: {filename}

Generate well-structured, production-ready code for this new file.
Include appropriate imports, docstrings, and error handling.

IMPORTANT: Make sure all functions and classes exported by this module are properly defined and accessible.
The tests for this module will be placed in a 'tests' directory and will import from this module.
Make sure your code can be imported correctly from a different directory.

{PYTHON_CODE_ONLY}
"""
    return await ask_agent(prompt)


async def generate_test_file(source_code, filename, test_directory=None):
    """Generate a test file for a given source file.
    
    Args:
        source_code (str): The source code to generate tests for
        filename (str): The name of the source file
        test_directory (str, optional): Directory where test will be placed. 
                                       None means same directory as source file
    """
    test_filename = f"test_{filename}"
    module_name = filename.replace(".py", "")
    
    # Determine import strategy based on test location
    if test_directory:
        import_strategy = f"""IMPORTANT: This test file will be in the '{test_directory}' directory.
Since the source file is in the parent directory, use:
```python
import sys
sys.path.append("..")  # Add parent directory to path
from {module_name} import *  # Or specific functions
```"""
    else:
        import_strategy = f"""IMPORTANT: This test file will be in the same directory as the source file.
Use direct imports like:
```python
from {module_name} import *  # Or specific functions
```"""
    
    prompt = f"""Create a test file for the following Python code:

Source code ({filename}):
```python
{source_code}
```

Generate comprehensive pytest test cases that cover all functionality in the source file.
The test filename will be: {test_filename}

{import_strategy}

Include appropriate imports and test functions.
{PYTHON_CODE_ONLY}
"""
    return await ask_agent(prompt, agent=test_agent)


async def modify_code(code, instruction, test_output=None):
    if test_output:
        prompt = f"""You are modifying this Python code based on feedback.

Original code:
```python
{code}
```

Instruction:
{instruction}

Previous attempt failed with this test output:
{test_output}

{PYTHON_CODE_ONLY}
"""
    else:
        prompt = f"""You are modifying Python code.

Original code:
```python
{code}
```

Instruction:
{instruction}

{PYTHON_CODE_ONLY}
"""
    return await ask_agent(prompt)


async def generate_tests(code, test_code, instruction):
    prompt = f"""You are writing test cases for Python code.

Source code:
```python
{code}
```

Existing test code:
```python
{test_code}
```

Instruction:
{instruction}

Write or update test cases based on the instruction. Make sure to test new functionality 
while preserving tests for existing functionality. {PYTHON_CODE_ONLY}
"""
    
    return await ask_agent(prompt, agent=test_agent)