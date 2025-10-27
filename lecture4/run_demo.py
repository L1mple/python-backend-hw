#!/usr/bin/env python3
"""
Скрипт для запуска демонстрации уровней изоляции транзакций

Запуск: python run_demo.py
"""

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from transaction_demo import main

if __name__ == "__main__":
    print("🚀 Запуск демонстрации проблем транзакций...")
    print("📝 Убедитесь, что у вас установлены зависимости:")
    print("   pip install sqlalchemy")
    print()
    
    try:
        main()
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Убедитесь, что файл shop_api/main.py существует")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("💡 Проверьте настройки базы данных")
