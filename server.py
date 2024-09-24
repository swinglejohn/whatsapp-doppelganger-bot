"""Make some requests to OpenAI's chatbot"""

import flask
from flask import g

PORT = 5001
APP = flask.Flask(__name__)


@APP.route("/chat", methods=["GET"])
def chat():
    message = flask.request.args.get("q")
    print("Sending message: ", message)

    response = input(
        f"Here was the message: {message}\n\nWhat would you like to respond with?\n"
    )

    print("Response: ", response)
    return response


def start():
    APP.run(port=PORT, threaded=False)


if __name__ == "__main__":
    start()
