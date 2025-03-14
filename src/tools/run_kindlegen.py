#!/usr/bin/env python3
# kindle_dict\src\tools\run_kindlegen.py

import subprocess
import sys
import os

def run_kindlegen(opf_file, output_file=None):
    """
    Run kindlegen.exe through Wine, redirecting stderr to /dev/null.
    
    Args:
        opf_file: Path to the .opf file
        output_file: Optional output file name
    
    Returns:
        True if successful, False otherwise
    """
    # Construct command
    command = ['wine', os.path.join(os.path.dirname(__file__), 'kindlegen.exe')]
    command.append(opf_file)
    
    if output_file:
        command.extend(['-o', output_file])
    
    try:
        # Run command and redirect stderr to /dev/null
        with open(os.devnull, 'w') as devnull:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=devnull,
                text=True,
                check=False
            )
        
        # Check if output file was created
        if result.returncode <= 1:  # 0 = success, 1 = success with warnings
            print(result.stdout)
            return True
        else:
            print(f"Error running kindlegen: {result.stdout}")
            return False
    
    except Exception as e:
        print(f"Exception running kindlegen: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_kindlegen.py <opf_file> [<output_file>]")
        sys.exit(1)
    
    opf_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = run_kindlegen(opf_file, output_file)
    sys.exit(0 if success else 1)