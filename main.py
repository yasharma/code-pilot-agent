import subprocess
import time
import asyncio
import os
import glob

from dotenv import load_dotenv

from agent import (
    modify_code, 
    generate_tests, 
    check_functionality_exists, 
    determine_file_action,
    generate_new_file,
    generate_test_file
)
# Load environment variables from .env file
load_dotenv()

MAX_RETRIES = 3
# Default files that can be overridden
DEFAULT_FILE_PATH = "calc.py"
DEFAULT_TEST_PATH = "tests/test_calc.py"

# Make sure the tests directory exists
os.makedirs("tests", exist_ok=True)

INSTRUCTION = """
    create a new class which can handle http operations, it should have methods for get, post, put and delete"""


def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def write_file(path, content):
    # Ensure directory exists for the file
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def run_tests(test_path):
    result = subprocess.run(["pytest", test_path], capture_output=True, text=True)
    return result.stdout, result.returncode


def get_python_files():
    """Get all Python files in the current directory."""
    py_files = glob.glob("*.py")
    # Remove test files from the main list
    py_files = [f for f in py_files if not f.startswith("test_")]
    return py_files


def get_test_path(source_path):
    """Convert a source file path to test file path."""
    base_name = os.path.basename(source_path)
    test_file = f"test_{base_name}"
    return os.path.join("tests", test_file)


async def update_existing_file(file_path, instruction):
    """Update an existing file and its tests based on the instruction."""
    test_path = get_test_path(file_path)
    
    code = read_file(file_path)
    test_code = read_file(test_path)
    
    # First check if functionality already exists
    functionality_exists = await check_functionality_exists(code, instruction)
    
    if functionality_exists:
        print(f"✅ Required functionality already exists in {file_path}!")
        
        # Check if tests for this functionality exist too
        existing_tests_cover_it = await check_functionality_exists(test_code, f"Tests for: {instruction}")
        
        if existing_tests_cover_it:
            print("✅ Tests for this functionality also exist!")
            
            # Run the tests to confirm everything works
            test_output, code_result = run_tests(test_path)
            print(test_output)
            
            if code_result == 0:
                print("✅ All tests passed! No changes needed.")
                return True
            else:
                print("⚠️ Tests failed despite functionality existing. Will try to fix...")
        else:
            print("⚠️ Functionality exists but tests are missing. Will add tests...")
            # Generate tests for existing functionality
            updated_test_code = await generate_tests(code, test_code, instruction)
            write_file(test_path, updated_test_code)
            print("✅ Added tests for existing functionality.")
            return True
    
    # If we reach here, we need to add or fix the functionality
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🔁 Attempt {attempt}")
        
        # Pass test output to the model on retries after first attempt
        if attempt > 1:
            test_output, _ = run_tests(test_path)
            updated_code = await modify_code(code, instruction, test_output)
        else:
            updated_code = await modify_code(code, instruction)
            
        # Also generate or update test cases
        updated_test_code = await generate_tests(updated_code, test_code, instruction)
            
        # Write both updated files
        write_file(file_path, updated_code)
        write_file(test_path, updated_test_code)
        
        # Run tests to see if they pass
        test_output, code_result = run_tests(test_path)
        print(test_output)

        if code_result == 0:
            print("✅ All tests passed!")
            return True
        else:
            print("❌ Tests failed. Retrying...")
            code = updated_code
            test_code = updated_test_code
            time.sleep(1)

    print("❗Max retries reached. Agent failed.")
    return False


async def create_new_file(filename, instruction):
    """Create a new file and its corresponding test file based on the instruction."""
    print(f"🆕 Creating new file: {filename}")
    
    # Generate the source code for the new file
    source_code = await generate_new_file(instruction, filename)
    
    # Generate tests for the new file
    test_filename = get_test_path(filename)
    test_code = await generate_test_file(source_code, filename)
    
    # Write both files
    write_file(filename, source_code)
    write_file(test_filename, test_code)
    
    # Run tests to see if they pass
    test_output, code_result = run_tests(test_filename)
    print(test_output)
    
    if code_result == 0:
        print(f"✅ Created {filename} and {test_filename} successfully! All tests passed.")
        return True
    else:
        print(f"⚠️ Created {filename} and {test_filename}, but tests failed.")
        
        # Try to fix the code with test feedback
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"\n🔁 Fix attempt {attempt}")
            
            updated_code = await modify_code(source_code, instruction, test_output)
            write_file(filename, updated_code)
            
            # Run tests again
            test_output, code_result = run_tests(test_filename)
            print(test_output)
            
            if code_result == 0:
                print("✅ Fixed the code! All tests passed.")
                return True
            
            source_code = updated_code
            time.sleep(1)
        
        print("❗Max retries reached. New file created but tests still failing.")
        return False


async def main():
    # Get list of Python files
    py_files = get_python_files()
    
    # Determine which file to use based on the instruction
    file_action = await determine_file_action(INSTRUCTION, py_files)
    
    print(f"📝 Action: {file_action['action']}")
    print(f"📄 File: {file_action['filename']}")
    print(f"🔍 Reason: {file_action['reason']}")
    
    if file_action['action'] == 'CREATE':
        # Create a new file
        success = await create_new_file(file_action['filename'], INSTRUCTION)
    else:
        # Modify an existing file
        file_to_modify = file_action['filename']
        success = await update_existing_file(file_to_modify, INSTRUCTION)
    
    if success:
        print("\n✅ Task completed successfully!")
    else:
        print("\n❌ Task completed with issues.")


if __name__ == "__main__":
    asyncio.run(main())
