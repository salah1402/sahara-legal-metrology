import os
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv('backend/.env')

api_key = os.getenv('NVIDIA_API_KEY')
base_url = os.getenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1')
model = os.getenv('NVIDIA_MODEL', 'nvidia/nemotron-3-ultra-550b-a55b')

print(f"Connecting to {base_url} with model {model}...")

client = OpenAI(base_url=base_url, api_key=api_key)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful JSON assistant. Return only valid JSON."},
            {"role": "user", "content": "Return a JSON object with key 'status' set to 'connected' and 'model' set to your model name."}
        ],
        temperature=0.1,
        max_tokens=100
    )
    print("Direct Model Response:")
    print(response.choices[0].message.content)
    print("\nLive connection to NVIDIA Nemotron 3 Ultra 550B confirmed!")
except Exception as e:
    print(f"Model invocation failed: {e}")
