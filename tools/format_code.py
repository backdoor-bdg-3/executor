#!/usr/bin/env python3
"""
format_code.py - A script to automatically format C++ code using clang-format

This script:
1. Uses clang-format to format C++ files in the specified directory
2. Can be used either to check formatting or automatically fix issues
3. Can operate on all files or just modified files
4. Can be integrated into the build process or CI/CD pipeline
"""

import argparse
import os
import subprocess
import sys
import concurrent.futures
import difflib
from pathlib import Path
import re

# ANSI color codes
RESET = '\033[0m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
BOLD = '\033[1m'

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Format C++ code using clang-format')
    parser.add_argument('--source-dir', default='source/cpp',
                        help='Source directory to format (default: source/cpp)')
    parser.add_argument('--check', action='store_true',
                        help='Check format only (don\'t modify files)')
    parser.add_argument('--fix', action='store_true',
                        help='Fix formatting issues (default if --check not specified)')
    parser.add_argument('--all', action='store_true',
                        help='Process all files (not just modified ones)')
    parser.add_argument('--style', default='file',
                        help='Formatting style (default: file, which uses .clang-format)')
    parser.add_argument('--jobs', '-j', type=int, default=os.cpu_count(),
                        help=f'Number of parallel jobs (default: {os.cpu_count()})')
    parser.add_argument('--exclude', type=str, default='',
                        help='Regex pattern for files to exclude')
    return parser.parse_args()

def find_cpp_files(source_dir, all_files=False, exclude_pattern=None):
    """Find all C++ source files in the given directory."""
    cpp_files = []
    
    extensions = ('.cpp', '.h', '.hpp', '.c', '.cc', '.cxx', '.mm')
    
    if exclude_pattern:
        exclude_regex = re.compile(exclude_pattern)
    else:
        exclude_regex = None
    
    if all_files:
        # Process all files
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(extensions):
                    path = os.path.join(root, file)
                    if exclude_regex and exclude_regex.search(path):
                        continue
                    cpp_files.append(path)
    else:
        # Process only modified files
        try:
            # First try to get modified files from git
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                capture_output=True, text=True, check=True
            )
            modified = result.stdout.strip().split('\n')
            
            for file in modified:
                if file and file.endswith(extensions) and os.path.exists(file):
                    if exclude_regex and exclude_regex.search(file):
                        continue
                    if file.startswith(source_dir) or source_dir in file:
                        cpp_files.append(file)
            
            if not cpp_files:
                print(f"{YELLOW}No modified C++ files found. Run with --all to check all files.{RESET}")
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"{YELLOW}Could not get modified files from git. Checking all files...{RESET}")
            return find_cpp_files(source_dir, all_files=True, exclude_pattern=exclude_pattern)
    
    return cpp_files

def format_file(file, args):
    """Format a single file and return results."""
    result = {
        'file': file,
        'formatted': False,
        'diff': '',
        'error': None
    }
    
    try:
        # Read the original content
        with open(file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Run clang-format
        cmd = ['clang-format', f'-style={args.style}']
        
        process = subprocess.run(
            cmd,
            input=original_content,
            capture_output=True,
            text=True,
            check=True
        )
        
        formatted_content = process.stdout
        
        # Check if the file was reformatted
        if original_content != formatted_content:
            result['formatted'] = True
            
            # Generate diff
            diff = list(difflib.unified_diff(
                original_content.splitlines(),
                formatted_content.splitlines(),
                fromfile=f'a/{file}',
                tofile=f'b/{file}',
                lineterm=''
            ))
            result['diff'] = '\n'.join(diff)
            
            # Write the formatted content back if fixing
            if args.fix:
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

def main():
    """Main function."""
    args = parse_args()
    
    # Default to fix mode if not specified
    if not args.check and not args.fix:
        args.fix = True
    
    # Check if clang-format is installed
    try:
        subprocess.run(['clang-format', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{RED}Error: clang-format not found. Please install clang-format.{RESET}")
        print("  For macOS: brew install clang-format")
        print("  For Ubuntu: apt-get install clang-format")
        return 1
    
    # Check for .clang-format file if using 'file' style
    if args.style == 'file' and not os.path.exists('.clang-format'):
        # Create a basic .clang-format file
        print(f"{YELLOW}No .clang-format file found. Creating a default one...{RESET}")
        default_config = """---
BasedOnStyle: Google
AccessModifierOffset: -4
ColumnLimit: 100
IndentWidth: 4
TabWidth: 4
UseTab: Never
BreakBeforeBraces: Stroustrup
AllowShortIfStatementsOnASingleLine: false
AllowShortLoopsOnASingleLine: false
AllowShortFunctionsOnASingleLine: Inline
PointerAlignment: Left
SortIncludes: true
...
"""
        with open('.clang-format', 'w') as f:
            f.write(default_config)
    
    # Find C++ files to format
    cpp_files = find_cpp_files(args.source_dir, args.all, args.exclude)
    
    if not cpp_files:
        print(f"{GREEN}No C++ files found to format.{RESET}")
        return 0
    
    print(f"{BOLD}Running clang-format on {len(cpp_files)} files with {args.jobs} parallel jobs{RESET}")
    print(f"Mode: {'Checking' if args.check else 'Fixing'} formatting issues")
    
    # Format files in parallel
    formatted_files = []
    error_files = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_file = {executor.submit(format_file, file, args): file for file in cpp_files}
        
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result = future.result()
                
                if result['error']:
                    print(f"{RED}✗ {file}{RESET} (Error: {result['error']})")
                    error_files.append(file)
                elif result['formatted']:
                    formatted_files.append(file)
                    
                    if args.check:
                        print(f"{RED}✗ {file}{RESET} (Needs formatting)")
                        if result['diff']:
                            # Print a limited portion of the diff for better readability
                            diff_lines = result['diff'].split('\n')
                            if len(diff_lines) > 20:
                                diff_snippet = '\n'.join(diff_lines[:20]) + f"\n{YELLOW}... and {len(diff_lines)-20} more lines{RESET}"
                            else:
                                diff_snippet = result['diff']
                            
                            print(f"{BLUE}{diff_snippet}{RESET}")
                    else:
                        print(f"{GREEN}✓ {file}{RESET} (Formatted)")
                else:
                    print(f"{GREEN}✓ {file}{RESET} (Already formatted)")
                    
            except Exception as e:
                print(f"{RED}Error processing {file}: {str(e)}{RESET}")
                error_files.append(file)
    
    # Summary
    print(f"\n{BOLD}=== Summary ==={RESET}")
    print(f"Total files checked: {len(cpp_files)}")
    print(f"Files that needed formatting: {len(formatted_files)}")
    print(f"Files with errors: {len(error_files)}")
    
    if args.check and formatted_files:
        print(f"\n{YELLOW}Some files need formatting. Run with --fix to apply changes.{RESET}")
        return 1
    
    if error_files:
        print(f"\n{RED}Errors occurred while formatting some files.{RESET}")
        return 1
    
    if args.fix and formatted_files:
        print(f"\n{GREEN}Successfully formatted {len(formatted_files)} files.{RESET}")
    else:
        print(f"\n{GREEN}All files are properly formatted.{RESET}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
