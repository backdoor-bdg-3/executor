#!/usr/bin/env python3
"""
run-clang-tidy.py - A script to run clang-tidy on a source directory and perform fixes

This script:
1. Runs clang-tidy on all C++ files in a specified directory
2. Optionally fixes issues automatically where possible
3. Formats the output to be more readable
4. Generates a report of issues that need manual fixes
"""

import argparse
import json
import os
import subprocess
import sys
import re
import threading
import multiprocessing
from pathlib import Path

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run clang-tidy on a source directory')
    parser.add_argument('--source-dir', default='source/cpp', 
                        help='Source directory to analyze (default: source/cpp)')
    parser.add_argument('--include-dir', default='source/cpp', 
                        help='Include directory (default: source/cpp)')
    parser.add_argument('--fix', action='store_true', 
                        help='Apply automatic fixes')
    parser.add_argument('--fix-errors', action='store_true', 
                        help='Apply automatic fixes even for errors (not just warnings)')
    parser.add_argument('--all', action='store_true', 
                        help='Process all files (not just modified ones)')
    parser.add_argument('--checks', default='-*,bugprone-*,concurrency-*,core-*,modernize-*,performance-*,portability-*,-modernize-use-trailing-return-type',
                        help='Checks to run (default: modern+performance checks)')
    parser.add_argument('--jobs', '-j', type=int, default=multiprocessing.cpu_count(),
                        help=f'Number of parallel jobs (default: {multiprocessing.cpu_count()})')
    parser.add_argument('--output-report', default='clang-tidy-report.json',
                        help='Output JSON report path (default: clang-tidy-report.json)')
    return parser.parse_args()

def find_cpp_files(source_dir, all_files=False):
    """Find all C++ source files in the given directory."""
    cpp_files = []
    
    extensions = ('.cpp', '.h', '.hpp', '.c', '.cc', '.cxx', '.mm')
    
    if all_files:
        # Process all files
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(extensions):
                    cpp_files.append(os.path.join(root, file))
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
                    if file.startswith(source_dir) or source_dir in file:
                        cpp_files.append(file)
            
            if not cpp_files:
                print("No modified C++ files found. Run with --all to check all files.")
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Could not get modified files from git. Checking all files...")
            return find_cpp_files(source_dir, all_files=True)
    
    return cpp_files

def run_clang_tidy_on_file(file, args, results, lock):
    """Run clang-tidy on a single file and collect results."""
    clang_tidy_cmd = ['clang-tidy']
    
    if args.fix:
        clang_tidy_cmd.append('-fix')
    if args.fix_errors:
        clang_tidy_cmd.append('-fix-errors')
    
    clang_tidy_cmd.extend([
        f'-checks={args.checks}',
        f'-header-filter={args.include_dir}',
        '-p=.',  # Assume compile_commands.json is in current directory
        file
    ])
    
    # Create an entry for this file's results
    file_result = {
        'file': file,
        'success': False,
        'errors': [],
        'warnings': [],
        'notes': [],
        'raw_output': ''
    }
    
    try:
        # Run clang-tidy
        process = subprocess.run(
            clang_tidy_cmd,
            capture_output=True,
            text=True
        )
        
        file_result['raw_output'] = process.stdout + process.stderr
        
        # Parse output
        error_pattern = re.compile(r'(.*?):(\d+):(\d+): error: (.*)')
        warning_pattern = re.compile(r'(.*?):(\d+):(\d+): warning: (.*)')
        note_pattern = re.compile(r'(.*?):(\d+):(\d+): note: (.*)')
        
        for line in process.stdout.splitlines() + process.stderr.splitlines():
            error_match = error_pattern.match(line)
            warning_match = warning_pattern.match(line)
            note_match = note_pattern.match(line)
            
            if error_match:
                file_result['errors'].append({
                    'file': error_match.group(1),
                    'line': int(error_match.group(2)),
                    'column': int(error_match.group(3)),
                    'message': error_match.group(4)
                })
            elif warning_match:
                file_result['warnings'].append({
                    'file': warning_match.group(1),
                    'line': int(warning_match.group(2)),
                    'column': int(warning_match.group(3)),
                    'message': warning_match.group(4)
                })
            elif note_match:
                file_result['notes'].append({
                    'file': note_match.group(1),
                    'line': int(note_match.group(2)),
                    'column': int(note_match.group(3)),
                    'message': note_match.group(4)
                })
        
        file_result['success'] = process.returncode == 0
        
        # Print progress
        if file_result['errors'] or file_result['warnings']:
            color = '\033[31m' if file_result['errors'] else '\033[33m'
            reset = '\033[0m'
            status = f"{color}{'✗' if file_result['errors'] else '⚠'}{reset}"
        else:
            status = '\033[32m✓\033[0m'
        
        with lock:
            print(f"{status} {file}")
            
            # Print errors and warnings
            for error in file_result['errors']:
                print(f"    \033[31mError:\033[0m {error['message']}")
            for warning in file_result['warnings']:
                print(f"    \033[33mWarning:\033[0m {warning['message']}")
        
    except Exception as e:
        file_result['success'] = False
        file_result['errors'].append({
            'file': file,
            'line': 0,
            'column': 0,
            'message': f"Error running clang-tidy: {str(e)}"
        })
        
        with lock:
            print(f"\033[31m✗\033[0m {file} (Error running clang-tidy: {str(e)})")
    
    with lock:
        results.append(file_result)

def main():
    """Main function."""
    args = parse_args()
    
    # Check if clang-tidy is installed
    try:
        subprocess.run(['clang-tidy', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: clang-tidy not found. Please install clang-tidy.")
        print("  For macOS: brew install llvm")
        print("  For Ubuntu: apt-get install clang-tidy")
        return 1
    
    # Find C++ files to check
    cpp_files = find_cpp_files(args.source_dir, args.all)
    
    if not cpp_files:
        print(f"No C++ files found in {args.source_dir}")
        return 0
    
    print(f"Running clang-tidy on {len(cpp_files)} files with {args.jobs} parallel jobs")
    
    # Create directory for compile_commands.json if it doesn't exist
    if not os.path.exists('compile_commands.json'):
        print("Warning: compile_commands.json not found. This might cause clang-tidy to fail.")
        print("         Try running 'make clean && bear -- make' to generate it.")
    
    # Run clang-tidy in parallel
    results = []
    lock = threading.Lock()
    threads = []
    
    for file in cpp_files:
        thread = threading.Thread(
            target=run_clang_tidy_on_file,
            args=(file, args, results, lock)
        )
        threads.append(thread)
        thread.start()
        
        # Limit number of concurrent threads
        if len(threads) >= args.jobs:
            threads[0].join()
            threads.pop(0)
    
    # Wait for all threads to finish
    for thread in threads:
        thread.join()
    
    # Summarize results
    total_errors = sum(len(result['errors']) for result in results)
    total_warnings = sum(len(result['warnings']) for result in results)
    
    print("\n=== Summary ===")
    print(f"Files checked: {len(results)}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")
    
    # Write report
    if args.output_report:
        with open(args.output_report, 'w') as f:
            json.dump({
                'summary': {
                    'files_checked': len(results),
                    'total_errors': total_errors,
                    'total_warnings': total_warnings,
                },
                'results': results
            }, f, indent=2)
        
        print(f"\nDetailed report saved to {args.output_report}")
    
    # Return error if there are still errors after fixes
    if total_errors > 0:
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
