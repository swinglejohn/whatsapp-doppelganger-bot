import datetime
import os
import pickle

import flask
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

PORT = 5001
APP = flask.Flask(__name__)

# OpenAI API configuration
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Load the custom fine-tuned model name from .env
MODEL1 = os.getenv("OPENAI_MODEL_NAME1")
MODEL2 = os.getenv("OPENAI_MODEL_NAME2")
models = [MODEL1, MODEL2]

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
MESSAGE_RATE = 15
MESSAGE_COOLDOWN = 0

# Load disabled chat IDs
DISABLED_CHATS_FILE = "disabled_chats.txt"
DISABLED_CHATS = set()

def load_disabled_chats():
    global DISABLED_CHATS
    if os.path.exists(DISABLED_CHATS_FILE):
        with open(DISABLED_CHATS_FILE, "r") as f:
            DISABLED_CHATS = set(line.strip() for line in f)

load_disabled_chats()

@APP.route("/chat", methods=["GET"])
def chat():
    message = flask.request.args.get("q")
    chat_id = flask.request.args.get("chat_id")
    print(f"Received message from chat {chat_id}:\n", message)

    # Check if the chat is disabled
    if chat_id in DISABLED_CHATS:
        print(f"Chat {chat_id} is disabled. Not sending any message.")
        return "No Message"

    # Initialize chat history and cooldown if they don't exist
    if chat_id not in CHAT_HISTORIES:
        CHAT_HISTORIES[chat_id] = []
    if chat_id not in CHAT_COOLDOWNS:
        CHAT_COOLDOWNS[chat_id] = 0

    # Special trigger messages override the cooldown and context so the model will always respond
    wasTriggered = False
    model, max_context_messages, messages_to_predict = (
        MODEL2,
        MAX_CONTEXT_MESSAGES,
        MESSAGES_TO_PREDICT,
    )
    words = message.split()
    if len(words) > 1 and words[1].lower() in ("@fambot", "fambot"):
        print()
        print("Trigger message detected")
        wasTriggered = True
        params = words[2:5]
        if len(params) == 3:
            try:
                p1, p2, p3 = params
                model, max_context_messages, messages_to_predict = (
                    models[int(p1) - 1],
                    int(p2),
                    int(p3),
                )
                print(
                    f"Triggering with model {model}, max_context_messages {max_context_messages}, messages_to_predict {messages_to_predict}"
                )
            except:
                print("Invalid parameters for trigger message")
                print("Triggering with default parameters")

    # Add user message to history (unless it's a trigger message)
    if not wasTriggered:
        CHAT_HISTORIES[chat_id].append(message)

    # Check if there are enough messages in the history
    if len(CHAT_HISTORIES[chat_id]) < MIN_CONTEXT_MESSAGES and not wasTriggered:
        print(
            f"Not sending any message because there's only {len(CHAT_HISTORIES[chat_id])}/{MIN_CONTEXT_MESSAGES}"
        )
        return "No Message"

    CHAT_COOLDOWNS[chat_id] -= 1
    if CHAT_COOLDOWNS[chat_id] > 0 and not wasTriggered:
        print(
            f"Not sending any message because MESSAGE_COOLDOWN for chat {chat_id} is {CHAT_COOLDOWNS[chat_id]} and the MESSAGE_RATE is {MESSAGE_RATE}"
        )
        return "No Message"
    print()
    CHAT_COOLDOWNS[chat_id] = MESSAGE_RATE

    # Prepare context for GPT
    context = ""
    if max_context_messages > 0:
        context = "\n".join(
            [msg for msg in CHAT_HISTORIES[chat_id][-max_context_messages:]]
        )

    # Call OpenAI API
    response = client.chat.completions.create(
        model=model,
        messages=[
            # this system prompt is special because it is what we fine-tuned the model with (except X instead of 3)
            {"role": "system", "content": f"predict {messages_to_predict} messages"},
            {"role": "user", "content": context},
        ],
    )

    # Extract and process the response
    gpt_response = response.choices[0].message.content.strip()
    output_messages = []
    current_message = ""
    for line in gpt_response.split('\n'):
        if ':' in line.split()[0]:
            if current_message:
                output_messages.append(current_message.strip())
            current_message = line
        else:
            current_message += '\n' + line if current_message else line
    if current_message:
        output_messages.append(current_message.strip())

    # Add assistant messages to history
    for output in output_messages:
        CHAT_HISTORIES[chat_id].append(output)

    # Get current timestamp
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print()
    print(f"[{current_time}] SENDING MESSAGE TO CHAT {chat_id}:")
    print("CONTEXT:\n", context)
    print("RESPONSE:\n", gpt_response)
    print()

    formatted_response = "\n".join(output_messages)
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
