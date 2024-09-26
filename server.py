import datetime
import os
import pickle

import flask
from dotenv import load_dotenv
from flask import g
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

PORT = 5001
APP = flask.Flask(__name__)

# OpenAI API configuration
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Load the custom fine-tuned model name from .env
MODEL = os.getenv("OPENAI_MODEL_NAME2")

# Message history for each chat
CHAT_HISTORIES = {}
CHAT_COOLDOWNS = {}  # New dictionary to store cooldowns for each chat

# File to store chat histories
CHAT_HISTORIES_FILE = "chat_histories.pkl"

# Load chat histories from file if it exists
if os.path.exists(CHAT_HISTORIES_FILE):
    with open(CHAT_HISTORIES_FILE, "rb") as f:
        CHAT_HISTORIES = pickle.load(f)

# Minimum number of messages required for context
MIN_CONTEXT_MESSAGES = 20
MAX_CONTEXT_MESSAGES = 20
MESSAGES_TO_PREDICT = 3
MESSAGE_RATE = 10
MESSAGE_COOLDOWN = 0


@APP.route("/chat", methods=["GET"])
def chat():
    message = flask.request.args.get("q")
    chat_id = flask.request.args.get("chat_id")
    print(f"Received message from chat {chat_id}:\n", message)

    # Initialize chat history and cooldown if they don't exist
    if chat_id not in CHAT_HISTORIES:
        CHAT_HISTORIES[chat_id] = []
    if chat_id not in CHAT_COOLDOWNS:
        CHAT_COOLDOWNS[chat_id] = 0

    # Add user message to history
    CHAT_HISTORIES[chat_id].append(message)

    # Check if there are enough messages in the history
    if len(CHAT_HISTORIES[chat_id]) < MIN_CONTEXT_MESSAGES:
        print(
            f"Not sending any message because there's only {len(CHAT_HISTORIES[chat_id])}/{MIN_CONTEXT_MESSAGES}"
        )
        return "No Message"

    # Prepare context for GPT
    context = "\n".join(
        [msg for msg in CHAT_HISTORIES[chat_id][-MAX_CONTEXT_MESSAGES:]]
    )

    CHAT_COOLDOWNS[chat_id] -= 1
    if CHAT_COOLDOWNS[chat_id] > 0:
        print(
            f"Not sending any message because MESSAGE_COOLDOWN for chat {chat_id} is {CHAT_COOLDOWNS[chat_id]} and the MESSAGE_RATE is {MESSAGE_RATE}"
        )
        return "No Message"
    CHAT_COOLDOWNS[chat_id] = MESSAGE_RATE

    # Call OpenAI API
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            # this system prompt is special because it is what we fine-tuned the model with (except X instead of 3)
            {"role": "system", "content": f"predict {MESSAGES_TO_PREDICT} messages"},
            {"role": "user", "content": context},
        ],
    )

    # Extract and process the response
    gpt_response = response.choices[0].message.content.strip()
    output_messages = gpt_response.split("\n")

    # Add assistant messages to history
    for output in output_messages:
        CHAT_HISTORIES[chat_id].append(output)

    # Get current timestamp
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print()
    print(f"[{current_time}] Sending message to chat {chat_id}:")
    print("Context:\n", context)
    print("Response:\n", gpt_response)
    print()

    formatted_response = "\n".join([msg for msg in output_messages])
    return formatted_response


def start():
    APP.run(port=PORT, threaded=False, debug=True)


# Add a function to save chat histories on server shutdown
def save_chat_histories():
    with open(CHAT_HISTORIES_FILE, "wb") as f:
        pickle.dump(CHAT_HISTORIES, f)


# Register the shutdown function
APP.teardown_appcontext(lambda exception: save_chat_histories())

if __name__ == "__main__":
    start()
