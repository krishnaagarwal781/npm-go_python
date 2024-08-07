import requests

def save_data_to_concur(org_id: str, payload: dict):
    url = f"https://concur.adnan-qasim.me/data-element/post/{org_id}"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raises an error for 4xx/5xx responses
        return response.json()  # Returns the response as JSON
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {str(e)}")
        return None
