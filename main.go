package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"syscall"

	_ "github.com/mattn/go-sqlite3"
	"github.com/mdp/qrterminal/v3"
	"go.mau.fi/whatsmeow"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
	"google.golang.org/protobuf/proto"
)

type Config struct {
	SenderNames map[string]string `json:"senderNames"`
}

var config Config

func init() {
	// Load configuration
	configFile, err := ioutil.ReadFile("numbers-to-names.json")
	if err != nil {
		fmt.Println("Error reading config file:", err)
		return
	}

	err = json.Unmarshal(configFile, &config)
	if err != nil {
		fmt.Println("Error parsing config file:", err)
		return
	}
}

type MyClient struct {
	WAClient       *whatsmeow.Client
	eventHandlerID uint32
}

func (mycli *MyClient) register() {
	mycli.eventHandlerID = mycli.WAClient.AddEventHandler(mycli.eventHandler)
}

func (mycli *MyClient) eventHandler(evt interface{}) {
	switch v := evt.(type) {
	case *events.Message:
		newMessage := v.Message
		var msg string
		
		// Check if the message is a media message, extended text message, or regular conversation
		if imageMsg := newMessage.GetImageMessage(); imageMsg != nil {
			msg = "<Media omitted>"
			msg += " " + imageMsg.GetCaption()
		} else if videoMsg := newMessage.GetVideoMessage(); videoMsg != nil {
			msg = "<Media omitted>"
			msg += " " + videoMsg.GetCaption()
		} else if audioMsg := newMessage.GetAudioMessage(); audioMsg != nil {
			msg = "<Media omitted>"
			// audio doesn't have captions apparently
		} else if docMsg := newMessage.GetDocumentMessage(); docMsg != nil {
			msg = "<Media omitted>"
			msg += " " + docMsg.GetCaption()
		} else if extendedMsg := newMessage.GetExtendedTextMessage(); extendedMsg != nil {
			msg = extendedMsg.GetText()
		} else {
			msg = newMessage.GetConversation()
		}
		
		// Determine if the message is from a group or private chat
		var chat types.JID
		var senderName string
		chat = v.Info.Chat
		senderName = getSenderName(v.Info.Sender.User)
		if v.Info.IsGroup {
			fmt.Printf("Group message from %s in group %s: %s\n", senderName, v.Info.Chat.User, msg)
		} else {
			fmt.Printf("Private message from %s:  %s\n", senderName, msg)
		}

		if msg == "" {
			return
		}

		// Format the message
		formattedMsg := fmt.Sprintf("%s: %s", senderName, msg)

		// URL encode the formatted message and chat ID
		urlEncoded := url.QueryEscape(formattedMsg)
		chatIDEncoded := url.QueryEscape(chat.String())
		url := fmt.Sprintf("http://localhost:5001/chat?q=%s&chat_id=%s", urlEncoded, chatIDEncoded)

		// Make the request
		resp, err := http.Get(url)
		if err != nil {
			fmt.Println("Error making request:", err)
			return
		}
		// Read the response
		buf := new(bytes.Buffer)
		buf.ReadFrom(resp.Body)
		newMsg := buf.String()

		// Check if the response is "No Message"
		if newMsg == "No Message" {
			fmt.Println("Response: No Message")
			return
		}

		// encode out as a string
		response := &waProto.Message{Conversation: proto.String(string(newMsg))}
		fmt.Println("Response:", response)

		// Send the message to the chat (group or private)
		_, err = mycli.WAClient.SendMessage(context.Background(), chat, response)
		if err != nil {
			fmt.Println("Error sending message:", err)
		}
	}
}

func getSenderName(phoneNumber string) string {
	if name, ok := config.SenderNames[phoneNumber]; ok {
		return name
	}
	return phoneNumber // Return the phone number if no name is found
}

func main() {
	dbLog := waLog.Stdout("Database", "DEBUG", true)
	// Make sure you add appropriate DB connector imports, e.g. github.com/mattn/go-sqlite3 for SQLite
	container, err := sqlstore.New("sqlite3", "file:examplestore.db?_foreign_keys=on", dbLog)
	if err != nil {
		panic(err)
	}
	// If you want multiple sessions, remember their JIDs and use .GetDevice(jid) or .GetAllDevices() instead.
	deviceStore, err := container.GetFirstDevice()
	if err != nil {
		panic(err)
	}
	clientLog := waLog.Stdout("Client", "DEBUG", true)
	client := whatsmeow.NewClient(deviceStore, clientLog)
	// add the eventHandler
	mycli := &MyClient{WAClient: client}
	mycli.register()

	if client.Store.ID == nil {
		// No ID stored, new login
		qrChan, _ := client.GetQRChannel(context.Background())
		err = client.Connect()
		if err != nil {
			panic(err)
		}
		for evt := range qrChan {
			if evt.Event == "code" {
				// Render the QR code here
				// e.g. qrterminal.GenerateHalfBlock(evt.Code, qrterminal.L, os.Stdout)
				// or just manually `echo 2@... | qrencode -t ansiutf8` in a terminal
				qrterminal.GenerateHalfBlock(evt.Code, qrterminal.L, os.Stdout)
				//				fmt.Println("QR code:", evt.Code)
			} else {
				fmt.Println("Login event:", evt.Event)
			}
		}
	} else {
		// Already logged in, just connect
		err = client.Connect()
		if err != nil {
			panic(err)
		}
	}

	// Listen to Ctrl+C (you can also do something else that prevents the program from exiting)
	c := make(chan os.Signal)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c

	client.Disconnect()
}
