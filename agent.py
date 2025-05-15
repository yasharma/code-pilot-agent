from agents import Agent, Runner
# Create an agent for code modification
code_agent = Agent(
    name="Code Modifier",
    instructions="You are an expert at modifying Python code based on instructions. Return ONLY the Python code without any explanations or markdown formatting.",
)

test_agent = Agent(
    name="Test Writer",
    instructions="You are an expert at writing test cases for Python code. Return ONLY the Python test code without any explanations or markdown formatting.",
)

analysis_agent = Agent(
    name="Code Analyzer",
    instructions="You analyze code to determine if specific functionality already exists. Respond with only 'yes' or 'no' followed by a brief explanation."
)


async def ask_agent(prompt, agent=code_agent):
    result = await Runner.run(agent, input=prompt)
    return result.final_output.strip()


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
    response = await ask_agent(prompt, agent=analysis_agent)
    return response.lower().startswith("yes")


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

Fix the code and return ONLY the Python code without any explanations or markdown formatting.
Do not include any text like "Here's the modified code:" or explanations.
Return ONLY the raw Python code that should be saved directly to the file.
"""
    else:
        prompt = f"""You are modifying Python code.

Original code:
```python
{code}
```

Instruction:
{instruction}

Return ONLY the Python code without any explanations or markdown formatting.
Do not include any text like "Here's the modified code:" or explanations.
Return ONLY the raw Python code that should be saved directly to the file.
"""
    response = await ask_agent(prompt)
    
    # Strip any markdown code block formatting
    if response.startswith("```python"):
        response = response.replace("```python", "", 1)
    if response.startswith("```"):
        response = response.replace("```", "", 1)
    if response.endswith("```"):
        response = response[:-3]
        
    return response.strip()


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
while preserving tests for existing functionality. Return ONLY the Python test code 
without any explanations or markdown formatting.
"""
    
    response = await ask_agent(prompt, agent=test_agent)
    
    # Strip any markdown code block formatting
    if response.startswith("```python"):
        response = response.replace("```python", "", 1)
    if response.startswith("```"):
        response = response.replace("```", "", 1)
    if response.endswith("```"):
        response = response[:-3]
        
    return response.strip()