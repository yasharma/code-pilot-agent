from agents import Agent, Runner
import subprocess
import asyncio
import os

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


def run_tests_with_output(test_path):
    """Run tests and return output and return code."""
    try:
        # Use the virtual environment's python and pytest
        venv_python = ".venv/bin/python"
        if os.path.exists(venv_python):
            result = subprocess.run([venv_python, "-m", "pytest", test_path, "-v"], capture_output=True, text=True)
        else:
            # Fallback to system pytest
            result = subprocess.run(["pytest", test_path, "-v"], capture_output=True, text=True)
        return result.stdout + result.stderr, result.returncode
    except Exception as e:
        return f"Error running tests: {str(e)}", 1


def extract_error_details(test_output):
    """Extract meaningful error details from test output."""
    lines = test_output.split('\n')
    errors = []
    in_error_section = False
    
    for line in lines:
        if 'FAILED' in line or 'ERROR' in line:
            in_error_section = True
            errors.append(line)
        elif in_error_section and (line.startswith('E ') or line.startswith('> ')):
            errors.append(line)
        elif in_error_section and line.strip() == '':
            in_error_section = False
    
    return '\n'.join(errors) if errors else test_output


async def generate_code_with_retry(instruction, filename=None, existing_code="", max_retries=3, test_path=None):
    """
    Generate code with automatic retry on test failures.
    
    Args:
        instruction (str): The instruction for code generation
        filename (str, optional): Name of the file being generated/modified
        existing_code (str): Existing code to modify (empty for new files)
        max_retries (int): Maximum number of retry attempts
        test_path (str, optional): Path to test file for validation
    
    Returns:
        dict: Contains 'code', 'success', 'attempts', 'final_error'
    """
    current_code = existing_code
    final_error = None
    
    for attempt in range(1, max_retries + 1):
        print(f"🔄 Code generation attempt {attempt}/{max_retries}")
        
        try:
            if attempt == 1:
                # First attempt - generate fresh code
                if existing_code:
                    current_code = await modify_code(existing_code, instruction)
                else:
                    current_code = await generate_new_file(instruction, filename or "generated_file.py")
            else:
                # Retry with error feedback
                error_feedback = f"""
Previous attempt failed with the following errors:
{final_error}

Please fix these specific issues while maintaining the core functionality.
Focus on:
1. Syntax errors
2. Import issues  
3. Logic errors
4. Test compatibility
"""
                current_code = await modify_code(current_code, instruction + error_feedback)
            
            # If we have a test path, validate the code
            if test_path:
                # Write the code to a temporary location for testing
                temp_file = filename or "temp_generated.py"
                with open(temp_file, "w") as f:
                    f.write(current_code)
                
                # Run tests
                test_output, return_code = run_tests_with_output(test_path)
                
                if return_code == 0:
                    print(f"✅ Code generation successful on attempt {attempt}")
                    return {
                        'code': current_code,
                        'success': True,
                        'attempts': attempt,
                        'final_error': None
                    }
                else:
                    final_error = extract_error_details(test_output)
                    print(f"❌ Attempt {attempt} failed with errors:")
                    print(final_error)
                    
                    if attempt < max_retries:
                        await asyncio.sleep(1)  # Brief pause before retry
            else:
                # No test validation - assume success
                return {
                    'code': current_code,
                    'success': True,
                    'attempts': attempt,
                    'final_error': None
                }
                
        except Exception as e:
            final_error = f"Code generation error: {str(e)}"
            print(f"❌ Attempt {attempt} failed with exception: {final_error}")
            
            if attempt < max_retries:
                await asyncio.sleep(1)
    
    return {
        'code': current_code,
        'success': False,
        'attempts': max_retries,
        'final_error': final_error
    }


async def generate_tests_with_retry(source_code, instruction, filename, max_retries=3, existing_test_code=""):
    """
    Generate test code with automatic retry on syntax/import errors.
    
    Args:
        source_code (str): The source code to generate tests for
        instruction (str): Original instruction
        filename (str): Source filename
        max_retries (int): Maximum retry attempts
        existing_test_code (str): Existing test code to enhance
    
    Returns:
        dict: Contains 'code', 'success', 'attempts', 'final_error'
    """
    current_test_code = existing_test_code
    final_error = None
    
    for attempt in range(1, max_retries + 1):
        print(f"🔄 Test generation attempt {attempt}/{max_retries}")
        
        try:
            if attempt == 1:
                # First attempt
                if existing_test_code:
                    current_test_code = await generate_tests(source_code, existing_test_code, instruction)
                else:
                    current_test_code = await generate_test_file(source_code, filename, test_directory="tests")
            else:
                # Retry with error feedback
                error_feedback = f"""
Previous test generation failed with:
{final_error}

Please fix the test code to address these issues:
1. Import errors
2. Syntax errors
3. Test logic issues
4. Compatibility with the source code
"""
                current_test_code = await generate_tests(source_code, current_test_code, instruction + error_feedback)
            
            # Basic syntax validation
            try:
                compile(current_test_code, '<string>', 'exec')
                print(f"✅ Test generation successful on attempt {attempt}")
                return {
                    'code': current_test_code,
                    'success': True,
                    'attempts': attempt,
                    'final_error': None
                }
            except SyntaxError as e:
                final_error = f"Syntax error in generated tests: {str(e)}"
                print(f"❌ Test attempt {attempt} failed: {final_error}")
                
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            final_error = f"Test generation error: {str(e)}"
            print(f"❌ Test attempt {attempt} failed with exception: {final_error}")
            
            if attempt < max_retries:
                await asyncio.sleep(1)
    
    return {
        'code': current_test_code,
        'success': False,
        'attempts': max_retries,
        'final_error': final_error
    }


async def create_or_modify_with_retry(instruction, filename=None, existing_code="", max_retries=3):
    """
    High-level function that handles the complete code generation and testing flow with retries.
    
    Args:
        instruction (str): The instruction for what to implement
        filename (str, optional): Target filename
        existing_code (str): Existing code to modify (empty for new files)
        max_retries (int): Maximum retry attempts
    
    Returns:
        dict: Contains 'source_code', 'test_code', 'success', 'details'
    """
    print(f"🚀 Starting code generation with retry for: {instruction[:50]}...")
    
    # Step 1: Generate/modify source code
    source_result = await generate_code_with_retry(
        instruction=instruction,
        filename=filename,
        existing_code=existing_code,
        max_retries=max_retries
    )
    
    if not source_result['success']:
        return {
            'source_code': source_result['code'],
            'test_code': None,
            'success': False,
            'details': f"Source code generation failed after {source_result['attempts']} attempts: {source_result['final_error']}"
        }
    
    # Step 2: Generate test code
    test_result = await generate_tests_with_retry(
        source_code=source_result['code'],
        instruction=instruction,
        filename=filename or "generated_file.py",
        max_retries=max_retries
    )
    
    if not test_result['success']:
        print(f"⚠️ Test generation failed, but source code is available")
        return {
            'source_code': source_result['code'],
            'test_code': test_result['code'],
            'success': False,
            'details': f"Source code generated successfully, but test generation failed: {test_result['final_error']}"
        }
    
    return {
        'source_code': source_result['code'],
        'test_code': test_result['code'],
        'success': True,
        'details': f"Successfully generated both source and tests in {source_result['attempts']} source attempts and {test_result['attempts']} test attempts"
    }


def validate_python_code(code):
    """
    Basic validation of Python code syntax.
    
    Args:
        code (str): Python code to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        compile(code, '<string>', 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"
    except Exception as e:
        return False, f"Compilation error: {str(e)}"


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