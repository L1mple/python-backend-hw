import uvicorn
from shop_api.main import app

if __name__ == "__main__":
    print("Client: http://localhost:8000/chat-client")
    print("WebSocket endpoint: ws://localhost:8000/chat/{chat_name}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
