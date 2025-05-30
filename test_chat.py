import requests

def test_chat():
    url = "http://127.0.0.1:8000/chat"
    payload = {"message": "Hello", "history": []}
    response = requests.post(url, json=payload)
    print(response.json())

if __name__ == "__main__":
    test_chat() 