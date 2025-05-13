import subprocess
import time
from openai import OpenAI
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

client = OpenAI()

MAX_RETRIES = 3
FILE_PATH = "calc.py"
TEST_PATH = "test_calc.py"
INSTRUCTION = "Change the `add` function to subtract instead of add."


def read_file(path):
    with open(path, "r") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)


def run_tests():
    result = subprocess.run(["pytest", TEST_PATH], capture_output=True, text=True)
    return result.stdout, result.returncode


def ask_llm(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def modify_code(code, instruction, test_output=None):
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
    response = ask_llm(prompt)
    
    # Strip any markdown code block formatting
    if response.startswith("```python"):
        response = response.replace("```python", "", 1)
    if response.startswith("```"):
        response = response.replace("```", "", 1)
    if response.endswith("```"):
        response = response[:-3]
        
    return response.strip()


def main():
    code = read_file(FILE_PATH)
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🔁 Attempt {attempt}")
        
        # Pass test output to the model on retries after first attempt
        if attempt > 1:
            test_output, _ = run_tests()
            updated_code = modify_code(code, INSTRUCTION, test_output)
        else:
            updated_code = modify_code(code, INSTRUCTION)
            
        write_file(FILE_PATH, updated_code)
        test_output, code_result = run_tests()
        print(test_output)

        if code_result == 0:
            print("✅ All tests passed!")
            return
        else:
            print("❌ Tests failed. Retrying...")
            code = updated_code
            time.sleep(1)

    print("❗Max retries reached. Agent failed.")


if __name__ == "__main__":
    main()
