import flask
from flask import g
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

PORT = 5001
APP = flask.Flask(__name__)

# OpenAI API configuration
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Load the custom fine-tuned model name from .env
MODEL = os.getenv("OPENAI_MODEL_NAME")

# Message history
MESSAGE_HISTORY = []


@APP.route("/chat", methods=["GET"])
def chat():
    message = flask.request.args.get("q")
    print("Received message:\n", message)

    # Add user message to history
    MESSAGE_HISTORY.append({"role": "user", "content": message})

    # Prepare context for GPT
    context = "\n".join([msg["content"] for msg in MESSAGE_HISTORY[-20:]])

    print("Context:\n", context)

    # Call OpenAI API
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            # this system prompt is special because it is what we fine-tuned the model with (except X instead of 3)
            {"role": "system", "content": "predict 3 messages"},
            {"role": "user", "content": context},
        ],
    )

    # Extract and process the response
    gpt_response = response.choices[0].message.content.strip()
    output_messages = gpt_response.split("\n")

    # Add assistant messages to history
    for output in output_messages:
        MESSAGE_HISTORY.append({"role": "assistant", "content": output})

    print("Response:\n", gpt_response)
    return gpt_response


def start():
    APP.run(port=PORT, threaded=False)


if __name__ == "__main__":
    start()
