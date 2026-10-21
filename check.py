import os
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()


api_key = os.getenv("GEMINI_API_KEY_1")
genai.configure(api_key=api_key)

print("Tumhari API Key ke liye available models ki list:\n")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)