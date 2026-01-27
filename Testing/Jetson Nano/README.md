# Jetson Nano Testing

A modular test framework for running hardware and software tests on the Jetson Nano platform. This project provides a test runner that automatically discovers and executes test modules.

## Overview

This testing framework allows you to organize and run various hardware/software tests for the Jetson Nano. Test modules follow a naming convention (`*_test.py`) and are automatically discovered and executed by the main test runner.

## Features

- **Automatic Test Discovery**: Automatically finds all test modules matching the `*_test.py` pattern
- **Modular Design**: Easily add new test modules without modifying the main runner
- **Error Handling**: Comprehensive error reporting and test result summaries
- **Flexible Test Structure**: Supports multiple test function patterns

## Setup

### Prerequisites

- Python 3.7 or higher
- Jetson Nano or compatible hardware
- Camera hardware (for camera tests)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ethanluh/Behrend_UAS_2025-2026.git
cd "Jetson Nano Testing"
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running All Tests

To run all test modules in the directory:

```bash
python main.py
```

The test runner will:
1. Discover all `*_test.py` modules
2. Execute each test module
3. Display results and a summary

### Running Individual Tests

You can also run individual test modules directly:

```bash
python camera_test.py
```

## Creating Test Modules

To create a new test module, follow these guidelines:

1. **Naming Convention**: Name your file `[name]_test.py` (e.g., `sensor_test.py`, `motor_test.py`)

2. **Test Structure**: You can structure your test module in one of three ways:

   **Option A: Direct execution on import**
   ```python
   import cv2
   
   # Your test code here
   print("Running test...")
   ```

   **Option B: Define a `test()` function**
   ```python
   def test():
       print("Running test...")
       # Your test code here
   ```

   **Option C: Define a `run_test()` function**
   ```python
   def run_test():
       print("Running test...")
       # Your test code here
   ```

3. **Example Test Module**:
   ```python
   # my_hardware_test.py
   import time
   
   def test():
       print("Testing hardware component...")
       # Your test logic here
       print("Test completed successfully!")
   ```

## Current Test Modules

- **camera_test.py**: Tests camera functionality using OpenCV
  - Displays live camera feed
  - Press 'q' to quit
  - Verifies camera initialization and frame capture

## Project Structure

```
Jetson Nano Testing/
├── main.py              # Test runner that discovers and executes tests
├── camera_test.py       # Camera functionality test
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Dependencies

- `opencv-python>=4.8.0` - Computer vision library for camera tests

## Contributing

When adding new test modules:

1. Follow the `*_test.py` naming convention
2. Ensure proper error handling
3. Add descriptive print statements for test progress
4. Update this README with your new test module description

## Troubleshooting

### Camera Not Found
If camera tests fail, ensure:
- Camera is properly connected
- Camera permissions are set correctly
- No other applications are using the camera

### Import Errors
If you encounter import errors:
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python version compatibility

## License

[Add your license information here]

