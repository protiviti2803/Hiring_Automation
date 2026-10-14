import os
from openai import OpenAI

key = None
with open(".env", "r") as f:
    for line in f:
        if "GROQ_API_KEY" in line:
            key = line.split("=")[1].strip()
            break

print("Extracted Key:", key)

try:
    client = OpenAI(
        api_key=key,
        base_url="https://api.groq.com/openai/v1"
    )
    models = client.models.list()
    for m in models.data:
        print(m.id)
except Exception as e:
    print("Failed listing models:", e)
