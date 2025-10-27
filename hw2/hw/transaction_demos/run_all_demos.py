"""
Run all transaction isolation demonstration scripts.
"""

import subprocess
import sys
from pathlib import Path

demos = [
    ("01_dirty_read_demo.py", "Dirty Read Problem"),
    ("02_no_dirty_read_demo.py", "Preventing Dirty Read"),
    ("03_non_repeatable_read_demo.py", "Non-Repeatable Read Problem"),
    ("04_no_non_repeatable_read_demo.py", "Preventing Non-Repeatable Read"),
    ("05_phantom_read_demo.py", "Phantom Read Problem"),
    ("06_no_phantom_read_demo.py", "Preventing Phantom Read"),
]

demo_dir = Path(__file__).parent

print("=" * 80)
print("RUNNING ALL TRANSACTION ISOLATION DEMONSTRATIONS")
print("=" * 80)
print()

for script, description in demos:
    script_path = demo_dir / script
    print(f"\n{'=' * 80}")
    print(f"Running: {description}")
    print(f"Script: {script}")
    print('=' * 80)
    print()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=demo_dir.parent,
            capture_output=False,
            text=True
        )
        if result.returncode != 0:
            print(f"⚠️  Warning: Script exited with code {result.returncode}")
    except Exception as e:
        print(f"❌ Error running {script}: {e}")

    print("\nPress Enter to continue to next demo...")
    input()

print("\n" + "=" * 80)
print("ALL DEMONSTRATIONS COMPLETED")
print("=" * 80)
