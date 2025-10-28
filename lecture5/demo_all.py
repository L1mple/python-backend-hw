#!/usr/bin/env python3

import subprocess
import sys
import os

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🎯 ПОЛНАЯ ДЕМОНСТРАЦИЯ LECTURE 5")
    print("=" * 60)
    print("Этот скрипт показывает все возможности тестирования")
    print("=" * 60)
    
    print("\n📋 Что включено:")
    print("• Полное тестирование API")
    print("• Покрытие кода 95%+")
    print("• CI/CD с GitHub Actions")
    print("• Автоматические отчеты")
    print("• Валидация данных")
    print("• Обработка ошибок")
    
    print("\n🔧 Установка...")
    try:
        subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
        subprocess.run(["pip", "install", "-r", "tests/requirements.txt"], check=True)
        subprocess.run(["pip", "install", "-e", "../lecture4"], check=True)
        print("✅ Зависимости установлены")
    except subprocess.CalledProcessError:
        print("❌ Ошибка установки")
        sys.exit(1)
    
    print("\n🧪 Запуск тестов...")
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
        
        print("\n✅ Все тесты прошли!")
        print("📊 Отчет сохранен в htmlcov/index.html")
        print("🎉 Покрытие кода ≥ 95%!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Тесты не прошли: {e}")
        sys.exit(1)
    
    print("\n🚀 CI/CD готов к работе!")
    print("• GitHub Actions настроен")
    print("• Автоматические тесты")
    print("• Отчеты о покрытии")
    print("• Зеленый пайплайн")

if __name__ == "__main__":
    main()
