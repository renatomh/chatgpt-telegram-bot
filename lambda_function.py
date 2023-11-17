# Function dependencies
import json
import os
import telebot
import openai
import logging
import boto3
import base64
import requests

# Setting up the loggers
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initializing the Bot
bot = telebot.TeleBot(os.environ["BOT_TOKEN"])

# Setting the API Key and model engine for OpenAI
openai.api_key = os.environ["OPENAI_API_KEY"]
model_engine = "gpt-3.5-turbo-1106"


# Function to get image from URL as base64
def url_to_base64(url):
    try:
        # Fetch the image from the URL
        response = requests.get(url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Encode the image content as base64
            base64_image = base64.b64encode(response.content).decode("utf-8")
            return base64_image
        else:
            logger.error(f"Failed to fetch image. Status code: {response.status_code}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    # If no image could be encoded, we return Nne
    return None


# This function checks if the message was sent by the admin
def is_admin_message(message):
    # Comparing the user ID and the defined admin chat ID
    if message["chat"]["id"] != int(os.environ["ADMIN_CHAT_ID"]):
        bot.send_message(
            message["chat"]["id"],
            "Currently, only the admin has access to this feature.",
        )
        return False
    return True


# Function to get messages from DynamoDN table
def get_dynamodb_messages():
    # Initializing DynamoDB instance and getting table
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
    table = dynamodb.Table(os.environ["AWS_DYNAMODB"])
    scan = table.scan()
    # Getting messages formatted as dict
    dynamo_messages = scan["Items"][0]["messages"]

    # Returning resulting dict
    return dynamo_messages


# Function to update the messages list on DynamoDB table
def update_dynamo_messages(message):
    # Initializing DynamoDB instance and getting table
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
    table = dynamodb.Table(os.environ["AWS_DYNAMODB"])

    # Getting the required item with the list of messages to be updated
    res = table.get_item(Key={"field": "messages"})
    item = res["Item"]

    # Appending the new message to the list
    # Must be formatted as one of the following:
    # {"role": "user", "content": "Text content'}
    # {"role": "assistant", "content": "Text content'}
    item["messages"].append(message)

    # Updating item in the table
    table.put_item(Item=item)


# Function to clear previous saved messages on DynamoDB table
def clear_dynamo_messages():
    # Initializing DynamoDB instance and getting table
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
    table = dynamodb.Table(os.environ["AWS_DYNAMODB"])

    # Getting the required item with the list of messages to be updated
    res = table.get_item(Key={"field": "messages"})
    item = res["Item"]

    # Clearing the list of items
    item["messages"] = []

    # Updating item in the table
    table.put_item(Item=item)

    # Clearing the local messages list
    global messages
    messages = []


# Initial/welcome message handler
def send_welcome(message):
    bot.send_message(
        message["chat"]["id"],
        f"Hello, {message['chat']['first_name']}, welcome to the personal ChatGPT Telegram Chatbot!",
    )


# Command to clear current conversation
def clear_messages(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        # Clearing the current conversation
        clear_dynamo_messages()
        bot.send_message(message["chat"]["id"], "Conversation was cleared!")


# Image generation request handler
def request_image(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        # Getting the text from the message
        text = message["text"].strip()
        # If no content was provided
        if text == "/image":
            bot.send_message(
                message["chat"]["id"],
                "Please provide a prompt for the image generation.",
            )
        # If a prompt was provided
        else:
            # We'll extract the prompt from the message text
            prompt = text.replace("/image", "")

            # If the content is too short
            if len(prompt) < 10:
                bot.send_message(
                    message["chat"]["id"], "Prompt is too short (min length: 10 chars)."
                )

            # If everything is ok, we'll try to generate the image and return to the user
            else:
                try:
                    # Requesting the image generation
                    response = openai.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1,
                    )
                    # Getting the image URL
                    image_url = response.data[0].url
                    # Getting the revised prompt to be sent as a caption
                    caption = response.data[0].revised_prompt
                    # Send the generated image back to the user
                    bot.send_photo(
                        message["chat"]["id"],
                        photo=image_url,
                        caption=caption,
                    )
                # If something goes wrong, we'll inform about the error
                except Exception as e:
                    bot.send_message(
                        message["chat"]["id"],
                        f"Error trying to generate the image: {e}",
                    )


# Visual input messages handler
def visual_input(message):
    try:
        # Checking if a image caption was provided
        if message["caption"] is None:
            bot.send_message(
                message["chat"]["id"],
                'Please, provide some context for the image as captions, e.g.: "What this image represents?"',
            )
            return

        # Getting the image path
        file_info = bot.get_file(message["photo"][-1]["file_id"])

        # Creating the image URL for the photo
        image_url = f"https://api.telegram.org/file/bot{os.environ['BOT_TOKEN']}/{file_info.file_path}"

        # Getting the image encoded as base64
        base64_image = url_to_base64(image_url)

        # If no image was returned
        if base64_image is None:
            bot.send_message(message["chat"]["id"], "The image could not be retrieved.")
            return

        # Defining the headers for the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        }

        # Defining the payload for the visual input completion request
        payload = {
            # Defining the required model for the request
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        # Including the message sent by the user
                        {"type": "text", "text": message["caption"]},
                        # Including the image sent by the user
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 300,
        }

        # Making the request to the API
        res = requests.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )

        # If an error occurs while requesting the API
        if res.status_code != 200:
            bot.send_message(
                message["chat"]["id"], "There was an error while parsing the image."
            )
            return

        # Replying with the API response contet
        bot.send_message(
            message["chat"]["id"], res.json()["choices"][0]["message"]["content"]
        )

        # Defining user message for the conversation
        user_message = {
            "role": "user",
            "content": message["caption"],
        }
        # Defining bot response for the conversation
        bot_message = {
            "role": "assistant",
            "content": res.json()["choices"][0]["message"]["content"],
        }
        # Adding the newly received and generated messages to the DynamoDB table in order to provide to the chatbot
        update_dynamo_messages(user_message)
        update_dynamo_messages(bot_message)

    # If something goes wrong
    except Exception as e:
        bot.send_message(
            message["chat"]["id"],
            f"There was an error while processing your request: {e}",
        )


# Main function
def lambda_handler(event, context):
    try:
        # Getting the message from the event
        message = json.loads(event["body"])["message"]

        # Split between three variables bellow

        # Chat ID will guide your chatbot reply
        chat_id = message["chat"]["id"]
        # Sender's first name, registered by user's Telegram app
        sender = message["from"]["first_name"]

        # Here, we check if it was a text message
        if "text" in message:
            # The message content
            text = message["text"]

            # Logging data about message received
            logger.info(sender)
            logger.info(text)

            # If user is sending an available command
            if text == "/start":
                send_welcome(message)
                return
            elif text == "/clear":
                clear_messages(message)
                return
            elif text.startswith("/image"):
                request_image(message)
                return

            # Otherwise, we'll save the message to the DynamoDB table
            update_dynamo_messages({"role": "user", "content": text})

            # Here, we'll talk to ChatGPT

            # First, we get the messages list
            messages = get_dynamodb_messages()
            # Making an API request to the OpenAI API
            res = openai.chat.completions.create(
                model=model_engine,
                messages=messages,
            )

            # Defining the response to be sent to the user
            response = res.choices[0].message.content
            # We'll also save the response to the DynamoDB table
            update_dynamo_messages({"role": "assistant", "content": response})

            # If desired, we can add the total tokens used on the request to the user
            response += f"\n\nTotal Tokens: {res.usage.total_tokens}"

            # Finally, we'll reply the user's message
            bot.send_message(chat_id, response)
            return

        # If a photo was sent
        elif "photo" in message:
            # We call the function to handle it
            visual_input(message)

        # Other types of messages/content is not supported currently
        else:
            bot.send_message(chat_id, "This type of content is not supported")

    # If something goes wrong
    except Exception as e:
        # We'll just log the error
        logger.error(e)
