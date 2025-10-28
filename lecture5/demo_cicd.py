#!/usr/bin/env python3

import subprocess
import sys
import os

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🚀 ДЕМОНСТРАЦИЯ CI/CD")
    print("=" * 60)
    print("Этот скрипт показывает, как работает CI/CD")
    print("=" * 60)
    
    print("\n📋 Что происходит в CI:")
    print("• Автоматический запуск тестов")
    print("• Проверка покрытия кода")
    print("• Генерация отчетов")
    print("• Уведомления о статусе")
    
    print("\n🔧 Триггеры:")
    print("• git push - запуск тестов")
    print("• pull request - проверка изменений")
    print("• manual - ручной запуск")
    
    print("\n📊 Результаты:")
    print("• ✅ Зеленый - все тесты прошли")
    print("• ❌ Красный - есть ошибки")
    print("• ⚠️ Желтый - предупреждения")
    
    print("\n🎯 Цели:")
    print("• Автоматизация тестирования")
    print("• Быстрая обратная связь")
    print("• Качество кода")
    print("• Уверенность в изменениях")

if __name__ == "__main__":
    main()
