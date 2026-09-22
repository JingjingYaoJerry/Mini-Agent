import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load environment variables from .env file


MODEL = "~openai/gpt-latest"  # specify the model to use


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

messages = []  # the messages i.e., the memory/context, that will be sent to the model

while True:
    user_input = input("User: ")  # get user input

    # The exit
    if user_input.strip().lower() in ("exit", "quit", "q"):
        print("Exiting the conversation...")
        break
    
    messages.append({"role": "user", "content": user_input})  # add user message

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer accurately and concisely."
            },  # the specification that should be understood by the model since the beginning
            
            *messages,  # unpack and include all previous messages in the conversation
        ]
    )

    response = completion.choices[0].message.content
    messages.append({"role": "assistant", "content": response})  # include the response
    print(f"LLM: {response}")