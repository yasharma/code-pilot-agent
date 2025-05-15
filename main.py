import subprocess
import time
import asyncio

from dotenv import load_dotenv

from agent import modify_code, generate_tests, check_functionality_exists
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
    test_code = read_file(TEST_PATH)
    
    # First check if functionality already exists
    functionality_exists = await check_functionality_exists(code, INSTRUCTION)
    
    if functionality_exists:
        print("✅ Required functionality already exists in the code!")
        
        # Check if tests for this functionality exist too
        existing_tests_cover_it = await check_functionality_exists(test_code, f"Tests for: {INSTRUCTION}")
        
        if existing_tests_cover_it:
            print("✅ Tests for this functionality also exist!")
            
            # Run the tests to confirm everything works
            test_output, code_result = run_tests()
            print(test_output)
            
            if code_result == 0:
                print("✅ All tests passed! No changes needed.")
                return
            else:
                print("⚠️ Tests failed despite functionality existing. Will try to fix...")
        else:
            print("⚠️ Functionality exists but tests are missing. Will add tests...")
            # Generate tests for existing functionality
            updated_test_code = await generate_tests(code, test_code, INSTRUCTION)
            write_file(TEST_PATH, updated_test_code)
            print("✅ Added tests for existing functionality.")
            return
    
    # If we reach here, we need to add or fix the functionality
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🔁 Attempt {attempt}")
        
        # Pass test output to the model on retries after first attempt
        if attempt > 1:
            test_output, _ = run_tests()
            updated_code = await modify_code(code, INSTRUCTION, test_output)
        else:
            updated_code = await modify_code(code, INSTRUCTION)
            
        # Also generate or update test cases
        updated_test_code = await generate_tests(updated_code, test_code, INSTRUCTION)
            
        # Write both updated files
        write_file(FILE_PATH, updated_code)
        write_file(TEST_PATH, updated_test_code)
        
        # Run tests to see if they pass
        test_output, code_result = run_tests()
        print(test_output)

        if code_result == 0:
            print("✅ All tests passed!")
            return
        else:
            print("❌ Tests failed. Retrying...")
            code = updated_code
            test_code = updated_test_code
            time.sleep(1)

    print("❗Max retries reached. Agent failed.")


if __name__ == "__main__":
    asyncio.run(main())
