from agents import Agent, Runner
# Create an agent for code modification
code_agent = Agent(
    name="Code Modifier",
    instructions="You are an expert at modifying Python code based on instructions. Return ONLY the Python code without any explanations or markdown formatting.",
)


async def ask_agent(prompt):
    result = await Runner.run(code_agent, input=prompt)
    return result.final_output.strip()


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