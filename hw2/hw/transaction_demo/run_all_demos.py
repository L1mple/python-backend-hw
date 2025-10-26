"""
Запускает все демонстрации подряд
"""
import asyncio
import subprocess
import sys
import os


async def run_demo(demo_file: str, title: str):
    print("\n" + "="*70)
    print(title)
    print("="*70)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    demo_path = os.path.join(script_dir, demo_file)
    
    result = subprocess.run([sys.executable, demo_path])
    return result.returncode == 0


async def main():
    demos = [
        ("01_dirty_read.py", "Dirty Read"),
        ("02_non_repeatable_read.py", "Non-Repeatable Read"),
        ("03_phantom_reads.py", "Phantom Reads"),
    ]
    
    for demo_file, title in demos:
        await run_demo(demo_file, title)
        if demo_file != demos[-1][0]:
            await asyncio.sleep(2)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
