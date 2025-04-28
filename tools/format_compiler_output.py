#!/usr/bin/env python3
"""
format_compiler_output.py - A script to format and colorize compiler output
"""

import sys
import re
import os
from collections import defaultdict

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

def is_error_line(line):
    """Check if a line contains an error message."""
    return " error:" in line or ": error:" in line

def is_warning_line(line):
    """Check if a line contains a warning message."""
    return " warning:" in line or ": warning:" in line

def is_note_line(line):
    """Check if a line contains a note message."""
    return " note:" in line or ": note:" in line

def colorize_line(line):
    """Add color to a compiler output line based on its content."""
    if not line.strip():
        return line
    
    # Highlight error lines
    if is_error_line(line):
        # Extract file, line, and column info using regex
        match = re.search(r'([^:]+):(\d+):(\d+):', line)
        if match:
            file_path, line_num, col_num = match.groups()
            file_name = os.path.basename(file_path)
            prefix = line[:match.start()]
            location = f"{file_path}:{line_num}:{col_num}:"
            rest = line[match.end():]
            
            # Replace "error:" with colored version
            rest = rest.replace("error:", f"{Colors.BOLD}{Colors.RED}error:{Colors.RESET}")
            
            return f"{prefix}{Colors.BOLD}{Colors.BLUE}{location}{Colors.RESET}{rest}"
        return f"{Colors.BOLD}{Colors.RED}{line}{Colors.RESET}"
    
    # Highlight warning lines
    elif is_warning_line(line):
        # Extract file, line, and column info using regex
        match = re.search(r'([^:]+):(\d+):(\d+):', line)
        if match:
            file_path, line_num, col_num = match.groups()
            file_name = os.path.basename(file_path)
            prefix = line[:match.start()]
            location = f"{file_path}:{line_num}:{col_num}:"
            rest = line[match.end():]
            
            # Replace "warning:" with colored version
            rest = rest.replace("warning:", f"{Colors.BOLD}{Colors.YELLOW}warning:{Colors.RESET}")
            
            return f"{prefix}{Colors.BOLD}{Colors.BLUE}{location}{Colors.RESET}{rest}"
        return f"{Colors.BOLD}{Colors.YELLOW}{line}{Colors.RESET}"
    
    # Highlight note lines
    elif is_note_line(line):
        # Extract file, line, and column info using regex
        match = re.search(r'([^:]+):(\d+):(\d+):', line)
        if match:
            file_path, line_num, col_num = match.groups()
            file_name = os.path.basename(file_path)
            prefix = line[:match.start()]
            location = f"{file_path}:{line_num}:{col_num}:"
            rest = line[match.end():]
            
            # Replace "note:" with colored version
            rest = rest.replace("note:", f"{Colors.BOLD}{Colors.CYAN}note:{Colors.RESET}")
            
            return f"{prefix}{Colors.BOLD}{Colors.BLUE}{location}{Colors.RESET}{rest}"
        return f"{Colors.BOLD}{Colors.CYAN}{line}{Colors.RESET}"
    
    # Colorize linker messages
    elif any(x in line for x in ["linking", "Linking", "ld: "]):
        return f"{Colors.MAGENTA}{line}{Colors.RESET}"
    
    # Colorize successful build messages
    elif any(x in line.lower() for x in ["successfully", "success", "built target"]):
        return f"{Colors.GREEN}{line}{Colors.RESET}"
    
    return line

def collect_issues(lines):
    """Collect all errors and warnings to display a summary."""
    errors = []
    warnings = []
    notes = []
    
    for line in lines:
        if is_error_line(line):
            errors.append(line)
        elif is_warning_line(line):
            warnings.append(line)
        elif is_note_line(line):
            notes.append(line)
    
    return errors, warnings, notes

def format_issues_by_file(issues):
    """Group issues by file for better readability."""
    by_file = defaultdict(list)
    
    for issue in issues:
        match = re.search(r'([^:]+):(\d+):(\d+):', issue)
        if match:
            file_path = match.group(1)
            by_file[file_path].append(issue)
        else:
            # For issues without file info
            by_file["unknown"].append(issue)
    
    return by_file

def print_summary(errors, warnings):
    """Print a summary of all errors and warnings."""
    if not errors and not warnings:
        print(f"\n{Colors.BOLD}{Colors.GREEN}✓ Build completed successfully with no issues{Colors.RESET}")
        return
    
    print(f"\n{Colors.BOLD}===== Build Summary ====={Colors.RESET}")
    
    if errors:
        print(f"\n{Colors.BOLD}{Colors.RED}Errors ({len(errors)}):{Colors.RESET}")
        errors_by_file = format_issues_by_file(errors)
        for file_path, file_errors in errors_by_file.items():
            print(f"\n{Colors.BOLD}In {Colors.BLUE}{file_path}{Colors.RESET}:")
            for i, error in enumerate(file_errors):
                # Extract just the error message, not the full line
                match = re.search(r'error: (.*)', error)
                if match:
                    error_msg = match.group(1)
                    print(f"  {Colors.RED}{i+1}.{Colors.RESET} {error_msg}")
                else:
                    print(f"  {Colors.RED}{i+1}.{Colors.RESET} {error}")
    
    if warnings:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}Warnings ({len(warnings)}):{Colors.RESET}")
        warnings_by_file = format_issues_by_file(warnings)
        for file_path, file_warnings in warnings_by_file.items():
            print(f"\n{Colors.BOLD}In {Colors.BLUE}{file_path}{Colors.RESET}:")
            for i, warning in enumerate(file_warnings):
                # Extract just the warning message, not the full line
                match = re.search(r'warning: (.*)', warning)
                if match:
                    warning_msg = match.group(1)
                    print(f"  {Colors.YELLOW}{i+1}.{Colors.RESET} {warning_msg}")
                else:
                    print(f"  {Colors.YELLOW}{i+1}.{Colors.RESET} {warning}")

def main():
    """Main function to process compiler output."""
    # Check if we're being used in a pipe
    if not sys.stdin.isatty():
        # Read all input lines
        lines = [line.rstrip('\n') for line in sys.stdin]
        
        # Collect all errors and warnings
        errors, warnings, notes = collect_issues(lines)
        
        # Output each line with color
        for line in lines:
            print(colorize_line(line))
        
        # Print a summary at the end
        print_summary(errors, warnings)
    else:
        print("This script is designed to be used in a pipe, e.g.:")
        print("  make |", sys.argv[0])

if __name__ == "__main__":
    main()
