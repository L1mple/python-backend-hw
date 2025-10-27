import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dirty_read import run_dirty_read
from non_repeatable_read import run_non_repeatable_read
from phantom_read import run_phantom_read

if __name__ == "__main__":
    print("Starting all isolation level tests...")

    run_dirty_read()
    run_non_repeatable_read()
    run_phantom_read()

    print("\nAll tests completed.")