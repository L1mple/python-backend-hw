#!/usr/bin/env python3

import subprocess
import sys
import os

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🚀 ДЕМОНСТРАЦИЯ CI/CD ДЛЯ SHOP API")
    print("=" * 60)
    print("Этот скрипт показывает, как настроен CI/CD для проекта")
    print("=" * 60)
    
    print("\n📋 Что настроено:")
    print("• GitHub Actions workflow")
    print("• Автоматический запуск тестов")
    print("• Проверка покрытия кода")
    print("• Отчеты о покрытии")
    print("• Уведомления о статусе")
    
    print("\n🔧 Команды для работы с CI:")
    print("• git push - запускает тесты автоматически")
    print("• git pull request - проверяет изменения")
    print("• make test - локальный запуск тестов")
    print("• make test-cov - тесты с покрытием")
    
    print("\n📊 Отчеты:")
    print("• HTML отчет: htmlcov/index.html")
    print("• Терминал: покрытие в консоли")
    print("• GitHub: статус в PR")
    
    print("\n🎯 Цели:")
    print("• Покрытие кода ≥ 95%")
    print("• Все тесты проходят")
    print("• Зеленый пайплайн")
    
    print("\n✅ CI/CD настроен и готов к работе!")

if __name__ == "__main__":
    main()
