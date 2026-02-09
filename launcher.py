import sys
import os
import multiprocessing

# Add src to sys.path so we can import the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mv_people.main import scan

if __name__ == "__main__":
    multiprocessing.freeze_support()
    scan()
