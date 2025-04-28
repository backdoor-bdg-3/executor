# Development Tools

This directory contains tools to enhance the development experience for the iOS executor project.

## Code Quality Tools

### 1. Compiler Output Formatter (`format_compiler_output.py`)

A Python script that formats and colorizes compiler output to make errors and warnings more readable.

**Usage:**
```bash
# Direct usage
./tools/format_compiler_output.py < compiler_output.txt

# Pipe compiler output directly
make | ./tools/format_compiler_output.py
```

**Features:**
- Colorizes error, warning, and note messages
- Shows file locations in a consistent format
- Provides a summary of all errors and warnings at the end
- Makes it easier to locate and fix compilation issues

### 2. Code Formatter (`format_code.py`)

Automatically formats C++ code using clang-format to maintain a consistent coding style.

**Usage:**
```bash
# Check if code is properly formatted (doesn't modify files)
./tools/format_code.py --check

# Fix formatting issues automatically
./tools/format_code.py --fix

# Format all files (not just modified ones)
./tools/format_code.py --all --fix
```

**Features:**
- Uses the project's `.clang-format` configuration
- Can work on just modified files (from git) or all files
- Parallel processing for faster formatting
- Detailed reporting of formatting changes

### 3. Static Analysis Tool (`run-clang-tidy.py`) 

Runs clang-tidy to perform static code analysis and automatically fix issues where possible.

**Usage:**
```bash
# Run analysis on all files
./tools/run-clang-tidy.py --all

# Run analysis with automatic fixes
./tools/run-clang-tidy.py --all --fix

# Run analysis with automatic fixes even for errors
./tools/run-clang-tidy.py --all --fix-errors
```

**Features:**
- Detects common coding errors and style violations
- Can automatically fix many issues
- Generates a JSON report of issues that require manual fixes
- Parallel processing for faster analysis

## Makefile Integration

These tools are integrated into the build system. You can use them through Makefile targets:

```bash
# Format code
make format

# Check format without modifying files
make format-check

# Run static analysis
make analyze

# Run static analysis with automatic fixes
make fix-analysis
```

When building the project, compiler output is automatically colorized and formatted for better readability.

## Requirements

- Python 3
- clang-format (for code formatting)
- clang-tidy (for static analysis)
- bear (to generate compile_commands.json for clang-tidy)

To install these dependencies:

**macOS:**
```bash
brew install llvm clang-format bear
```

**Ubuntu:**
```bash
apt-get install clang-format clang-tidy bear
```
