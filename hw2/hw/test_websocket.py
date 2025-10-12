import pytest
import asyncio
from fastapi.testclient import TestClient
from shop_api.main import app


def test_websocket_chat():
    client = TestClient(app)
    
    with client.websocket_connect("/chat/room1?username=Оленька") as websocket1:
        
        with client.websocket_connect("/chat/room1?username=Кузя") as websocket2:
            
            join_notification = websocket1.receive_text()
            assert "Кузя подключился к чату" in join_notification
            
            websocket1.send_text("Test")
            
            received_message_olenka = websocket1.receive_text()
            assert "Оленька :: Test" in received_message_olenka
            
            received_message_kuzia = websocket2.receive_text()
            assert "Оленька :: Test" in received_message_kuzia
            
            websocket2.send_text("Bu")
            
            received_reply_kuzia = websocket2.receive_text()
            assert "Кузя :: Bu" in received_reply_kuzia
            
            received_reply_olenka = websocket1.receive_text()
            assert "Кузя :: Bu" in received_reply_olenka


def test_websocket_different_rooms():
    client = TestClient(app)
    
    with client.websocket_connect("/chat/room1?username=User1") as websocket_room1:
        with client.websocket_connect("/chat/room2?username=User2") as websocket_room2:
            websocket_room1.receive_text()  
            websocket_room2.receive_text()  
            
            websocket_room1.send_text("Message from room1")
            websocket_room2.send_text("Message from room2")
                        
if __name__ == "__main__":
    test_websocket_chat()
    test_websocket_different_rooms()
