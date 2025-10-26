"""
Additional tests for WebSocket chat functionality to improve coverage.
"""

import pytest
from fastapi.testclient import TestClient
from shop_api.main import app

client = TestClient(app)


def test_websocket_chat_single_client():
    """Test WebSocket chat with a single client"""
    with client.websocket_connect("/chat/test-room") as websocket:
        # Send a message
        websocket.send_text("Hello, World!")

        # Receive the echoed message
        data = websocket.receive_text()
        assert "Hello, World!" in data
        # Message should include username
        assert "::" in data


def test_websocket_chat_multiple_clients():
    """Test WebSocket chat with multiple clients"""
    with client.websocket_connect("/chat/test-room-2") as ws1, \
         client.websocket_connect("/chat/test-room-2") as ws2:

        # Client 1 sends a message
        ws1.send_text("Message from client 1")

        # Both clients should receive the message
        msg1 = ws1.receive_text()
        msg2 = ws2.receive_text()

        assert "Message from client 1" in msg1
        assert "Message from client 1" in msg2

        # Client 2 sends a message
        ws2.send_text("Message from client 2")

        # Both clients should receive the message
        msg1 = ws1.receive_text()
        msg2 = ws2.receive_text()

        assert "Message from client 2" in msg1
        assert "Message from client 2" in msg2


def test_websocket_chat_history():
    """Test that chat history is sent to new clients"""
    # First client sends messages
    with client.websocket_connect("/chat/history-room") as ws1:
        ws1.send_text("First message")
        ws1.receive_text()  # Consume the echo

        ws1.send_text("Second message")
        ws1.receive_text()  # Consume the echo

    # Second client connects and should receive history
    with client.websocket_connect("/chat/history-room") as ws2:
        # Should receive historical messages
        msg1 = ws2.receive_text()
        msg2 = ws2.receive_text()

        assert "First message" in msg1
        assert "Second message" in msg2


def test_websocket_different_rooms():
    """Test that messages are isolated between different chat rooms"""
    with client.websocket_connect("/chat/room-a") as ws_a, \
         client.websocket_connect("/chat/room-b") as ws_b:

        # Send message in room A
        ws_a.send_text("Message in room A")
        msg_a = ws_a.receive_text()
        assert "Message in room A" in msg_a

        # Send message in room B
        ws_b.send_text("Message in room B")
        msg_b = ws_b.receive_text()
        assert "Message in room B" in msg_b

        # Rooms should be isolated (no cross-talk)
        assert "room B" not in msg_a
        assert "room A" not in msg_b


def test_websocket_disconnect_cleanup():
    """Test that disconnecting clients are properly cleaned up"""
    # Create and disconnect a client
    with client.websocket_connect("/chat/cleanup-room") as ws1:
        ws1.send_text("Test message")
        ws1.receive_text()
    # ws1 is now disconnected

    # Connect new client and send message
    with client.websocket_connect("/chat/cleanup-room") as ws2:
        # Should receive history first
        history_msg = ws2.receive_text()
        assert "Test message" in history_msg

        ws2.send_text("After disconnect")
        msg = ws2.receive_text()
        assert "After disconnect" in msg
