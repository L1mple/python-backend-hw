"""Pytest configuration and fixtures for test-hw"""
import os
import pytest

# Set TESTING environment variable before any imports
os.environ["TESTING"] = "1"
