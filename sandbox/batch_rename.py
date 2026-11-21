#!/usr/bin/env python3
import os
import sys

def batch_rename(prefix, directory):
    """
    Rename all .txt files in the given directory by adding the specified prefix.

    :param prefix: The prefix to add before each filename.
    :param directory: The directory to process.
    """
    if not os.path.isdir(directory):
        print(f"Error: The directory '{directory}' does not exist.")
        sys.exit(1)

    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            new_name = prefix + filename
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_name)
            os.rename(old_path, new_path)
            print(f"Renamed '{old_path}' to '{new_path}'")
        else:
            print(f"Skipping '{filename}' as it is not a .txt file.")

if __name__ == '__main__':
    batch_rename('bak_', 'sandbox/tmp')
