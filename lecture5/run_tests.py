#!/usr/bin/env python3

import subprocess
import sys
import os

def run_tests():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🧪 Запуск тестов для Shop API...")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            "pytest", 
            "tests/test_shop_api.py",
            "--cov=shop_api",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=95",
            "-v"
        ], check=True)
        
        print("\n✅ Все тесты прошли успешно!")
        print("📊 Отчет о покрытии сохранен в htmlcov/index.html")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Тесты не прошли: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ pytest не найден. Установите зависимости:")
        print("pip install -r requirements.txt")
        print("pip install -r tests/requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
