#!/usr/bin/env python3

import subprocess
import sys
import os

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("📊 ДЕМОНСТРАЦИЯ ПОКРЫТИЯ КОДА")
    print("=" * 60)
    print("Этот скрипт показывает, как работает покрытие кода")
    print("=" * 60)
    
    print("\n📋 Что такое покрытие:")
    print("• Процент кода, покрытого тестами")
    print("• Показывает, какой код тестируется")
    print("• Помогает найти непротестированные части")
    print("• Обеспечивает качество кода")
    
    print("\n🔧 Команды:")
    print("• --cov=module - покрытие модуля")
    print("• --cov-report=html - HTML отчет")
    print("• --cov-report=term - в терминале")
    print("• --cov-fail-under=95 - минимум 95%")
    
    print("\n📊 Отчеты:")
    print("• HTML: htmlcov/index.html")
    print("• Терминал: покрытие в консоли")
    print("• XML: coverage.xml")
    
    print("\n🎯 Цели:")
    print("• Покрытие ≥ 95%")
    print("• Все строки протестированы")
    print("• Качественные тесты")
    print("• Уверенность в коде")

if __name__ == "__main__":
    main()
