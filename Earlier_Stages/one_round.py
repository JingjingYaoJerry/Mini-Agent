from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file


MODEL = "~openai/gpt-latest"  # specify the model to use


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

completion = client.chat.completions.create(
    model=MODEL,
    messages=[
      {
          "role": "system",
          "content": "You are a helpful assistant. Answer accurately and concisely."
      },  # the specification that should be understood by the model since the beginning
      {
          "role": "user",
          "content": "Who are you, who do you think I am and where am I?"
      },  # the user prompt that should be answered by the model
      {
          "role": "assistant",
          "content": ""
      },  # the LLM's response to the user's prompt
    ]
)

print(completion.choices[0].message.content)