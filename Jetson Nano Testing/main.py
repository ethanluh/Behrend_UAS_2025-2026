import os
import importlib
import sys
from pathlib import Path

def discover_test_modules():
    """Discover all modules matching the pattern XXX_test.py in the current directory."""
    test_modules = []
    current_dir = Path(__file__).parent
    
    for file in current_dir.glob("*_test.py"):
        module_name = file.stem  # Get filename without extension
        test_modules.append(module_name)
    
    return sorted(test_modules)

def run_test_module(module_name):
    """Import and run a test module."""
    try:
        print(f"\n{'='*60}")
        print(f"Running test: {module_name}")
        print(f"{'='*60}")
        
        # Import the module
        module = importlib.import_module(module_name)
        
        # Try to run a test function if it exists
        if hasattr(module, 'run_test'):
            module.run_test()
        elif hasattr(module, 'test'):
            module.test()
        else:
            # If no test function exists, just importing should run the code
            # (for modules that run on import like camera_test.py)
            print(f"Module {module_name} executed on import")
        
        print(f"✓ {module_name} completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ {module_name} failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test runner function."""
    print("="*60)
    print("Test Runner - Discovering and running test modules")
    print("="*60)
    
    # Discover all test modules
    test_modules = discover_test_modules()
    
    if not test_modules:
        print("No test modules found matching pattern *_test.py")
        return
    
    print(f"\nFound {len(test_modules)} test module(s):")
    for module in test_modules:
        print(f"  - {module}")
    
    # Run each test module
    results = []
    for module_name in test_modules:
        success = run_test_module(module_name)
        results.append((module_name, success))
    
    # Print summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    for module_name, success in results:
        status = "PASSED" if success else "FAILED"
        print(f"  {module_name}: {status}")
    
    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}")
    print(f"{'='*60}")
    
    # Exit with error code if any tests failed
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()

