'''
Run this script to generate a single .txt file with all of the IPM code concatenated
Script only looks inside the "APPROVED_FOLDERS"

Script also only looks directly in the IPM parent folder, but no deeper if its
not on the approved list ie; it wont look in .venv etc.
'''

import os
from datetime import datetime

def collect_code():
    # Approved folders to look into
    APPROVED_FOLDERS = {'controllers', 'database', 'models', 'utils', 'views'}
    
    # Get the script's filename to exclude it
    script_name = os.path.basename(__file__)
    
    # Get the current directory (where the script is running)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(current_dir, f'code_collection_{timestamp}.txt')
    
    # Store all found files
    files_to_process = []
    
    # First, collect Python files from IPM root (excluding script itself)
    for file in os.listdir(current_dir):
        if file.endswith('.py') and file != script_name:
            full_path = os.path.join(current_dir, file)
            # Only include files, not directories
            if os.path.isfile(full_path):
                relative_path = file
                files_to_process.append((relative_path, full_path))

    # Then look into approved folders only
    for folder in APPROVED_FOLDERS:
        folder_path = os.path.join(current_dir, folder)
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # Get files only in this directory (not recursive)
            for file in os.listdir(folder_path):
                if file.endswith(('.py', '.sql')):
                    full_path = os.path.join(folder_path, file)
                    # Only include files, not directories
                    if os.path.isfile(full_path):
                        relative_path = os.path.join(folder, file)
                        files_to_process.append((relative_path, full_path))

    # Sort files by path for consistent output
    files_to_process.sort()

    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write(f"Code Collection - Created on {datetime.now()}\n")
        outfile.write("="*80 + "\n\n")
        
        for relative_path, full_path in files_to_process:
            try:
                with open(full_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    
                outfile.write(f"File: {relative_path}\n")
                outfile.write("-"*80 + "\n")
                outfile.write(content)
                outfile.write("\n\n" + "="*80 + "\n\n")
                
                print(f"Processed: {relative_path}")
            except Exception as e:
                print(f"Error processing {relative_path}: {str(e)}")

    print(f"\nCollection complete! Output saved to: {output_file}")
    print(f"Total files processed: {len(files_to_process)}")

if __name__ == "__main__":
    collect_code()