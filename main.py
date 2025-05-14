import subprocess
import time
import asyncio

from dotenv import load_dotenv

from agent import modify_code
# Load environment variables from .env file
load_dotenv()

MAX_RETRIES = 3
FILE_PATH = "calc.py"
TEST_PATH = "test_calc.py"
INSTRUCTION = """
    I want to create a new function which can return me output as a number, 
    example: user ask what is 5% of 100, it should return 5. another example: user ask what is 10% of 200, 
    it should return 20. please create a function which can do this. 
    please make sure to not change any other code in the file. just create the simple function in the file"""


def read_file(path):
    with open(path, "r") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)


def run_tests():
    result = subprocess.run(["pytest", TEST_PATH], capture_output=True, text=True)
    return result.stdout, result.returncode


async def main():
    code = read_file(FILE_PATH)
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🔁 Attempt {attempt}")
        
        # Pass test output to the model on retries after first attempt
        if attempt > 1:
            test_output, _ = run_tests()
            updated_code = await modify_code(code, INSTRUCTION, test_output)
        else:
            updated_code = await modify_code(code, INSTRUCTION)
            
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
    asyncio.run(main())
