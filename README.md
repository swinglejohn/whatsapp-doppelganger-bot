# whatsapp-doppelganger-bot

I forked this repo from Daniel Gross but it's doing something wildly different now. His repo was just a good starting bot for a WhatsApp bot. Also I didn't know about whatsmeow but it seems to work very well.

The purpose of this repo is to send messages in a WhatsApp group chat using an LLM fine-tuned (separate repo) on that chat.

## Initial setup
You can do pip install -r requirements.txt to install the python libraries 

Use this command to copy the template files:
`cp .template-env .env && cp .template-numbers-to-names.json numbers-to-names.json`
Open .env and fill in your API key and model names
Open numbers-to-names.json and add the names and numbers of everyone in the group chat

## Compiling
If you have a machine with > 1 GB of ram, you can just run the go code with `go run main.go`.

If, for cost reasons, you're running this on a t4g.nano, you will want to compile the code on your personal machine and then copy the binary to the t4g.nano. A t4g.nano has 0.5 GB of ram and is an ARM64 machine.

To compile the code you can run:
```
# 1. Install the ARM64 cross-compiler toolchain
sudo apt update
sudo apt install gcc-aarch64-linux-gnu

# 2. Install SQLite dev packages
sudo apt install libsqlite3-dev

# 3. Cross-compile with the correct environment variables
CGO_ENABLED=1 \
GOOS=linux \
GOARCH=arm64 \
CC=aarch64-linux-gnu-gcc \
go build main.go
```

## Running it
* You'll need to run WhatsApp from a phone number using the golang library I'm using. I just used my own WhatsApp account.
* Two terminals: `go run main.go`, and `python server.py`. I am extremely doubtful they will work for you on the first run. Ask chatGPT.
* This marks the end of the readme file; it is a bit sparse; thankfully the code is too! Just tuck in if you can... and I will try to add more here later.

## Chat commands

Start a text message with `fambot` or `@fambot` (case-insensitive).

- `fambot`: generate with defaults: model 3, up to 20 recent stored messages,
  and 2 predicted messages.
- `fambot <model> <context> <messages>`: override all three settings for this
  request. Model is 1, 2, or 3; context is how many recent stored messages to
  use (0 means none); messages is the requested number of predictions.
  For example, `fambot 2 40 3` uses model 2 with up to 40 messages of context
  and asks for 3 predictions. The actual number of predictions may vary.
- `fambot help`, `fambot --help`, or `fambot -h`: show usage, examples, and
  reply behavior. These also work with `@fambot`.

Help is a fixed response: no model call, no cooldown change, and no command
text added to chat history. Disabled chats stay silent. Explicit generation
triggers bypass the minimum history and cooldown; automatic generation needs
at least 20 stored messages and a cooldown of 1000 eligible incoming messages.

Run the isolated tests with `python -m unittest discover -s tests`.
