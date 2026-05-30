import requests

url = "https://openrouter.ai/api/v1/models"
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    free_models = [m['id'] for m in data['data'] if ':free' in m['id']]
    print("Available free models:")
    for m in free_models:
        print(f"- {m}")
else:
    print(f"Failed to fetch: {response.text}")
