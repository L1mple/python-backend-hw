#!/usr/bin/env python3

import subprocess
import sys
import os

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🧪 ДЕМОНСТРАЦИЯ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print("Этот скрипт показывает, как работают тесты")
    print("=" * 60)
    
    print("\n📋 Типы тестов:")
    print("• Unit тесты - тестирование отдельных функций")
    print("• Integration тесты - тестирование взаимодействия")
    print("• API тесты - тестирование HTTP endpoints")
    print("• Coverage тесты - проверка покрытия кода")
    
    print("\n🔧 Команды:")
    print("• pytest - запуск всех тестов")
    print("• pytest -v - подробный вывод")
    print("• pytest --cov - с покрытием")
    print("• pytest -k test_name - конкретный тест")
    
    print("\n📊 Отчеты:")
    print("• HTML: htmlcov/index.html")
    print("• Терминал: покрытие в консоли")
    print("• XML: coverage.xml")
    
    print("\n🎯 Цели:")
    print("• Покрытие ≥ 95%")
    print("• Все тесты проходят")
    print("• Быстрое выполнение")
    print("• Читаемые отчеты")

if __name__ == "__main__":
    main()