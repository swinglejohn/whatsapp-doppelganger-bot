# whatsapp-doppelganger-bot

I forked this repo from Daniel Gross but it's doing something wildly different now. His repo was just a good starting bot for a WhatsApp bot. Also I didn't know about whatsmeow but it seems to work very well.

The purpose of this repo is to send messages in a WhatsApp group chat using an LLM fine-tuned (separate repo) on that chat.

## Running it
* You'll need to run WhatsApp from a phone number using the golang library I'm using. I just used my own WhatsApp account.
* Two terminals: `go run main.go`, and `python server.py`. I am extremely doubtful they will work for you on the first run. Ask chatGPT.
* This marks the end of the readme file; it is a bit sparse; thankfully the code is too! Just tuck in if you can... and I will try to add more here later.
