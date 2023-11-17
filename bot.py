# -*- coding: utf-8 -*-
"""
Created on Mon Mar 13 11:50:00 2023

@author: Renato Henz

Telegram Chatbot server

"""

# Main dependencies
import telebot
import openai
import boto3
import base64
import requests
from dotenv import dotenv_values

# Getting the .env variables and keys
config = dotenv_values(".env")

# Instantiating the Telegram Chatbot object
bot = telebot.TeleBot(config["BOT_TOKEN"])

# Setting the API Key and model engine for OpenAI
openai.api_key = config["OPENAI_API_KEY"]
model_engine = "gpt-3.5-turbo-1106"

# Initializing the boto3 (AWS) session
session = boto3.Session(
    aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"],
)


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
            print(f"Failed to fetch image. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")
    # If no image could be encoded, we return Nne
    return None


# Function to get messages from DynamoDN table
def get_dynamodb_messages():
    # Initializing DynamoDB instance and getting table
    dynamodb = session.resource("dynamodb", region_name=config["AWS_REGION"])
    table = dynamodb.Table(config["AWS_DYNAMODB"])
    scan = table.scan()
    # Getting messages formatted as dict
    dynamo_messages = scan["Items"][0]["messages"]

    # Returning resulting dict
    return dynamo_messages


# Function to update the messages list on DynamoDB table
def update_dynamo_messages(message):
    # Initializing DynamoDB instance and getting table
    dynamodb = session.resource("dynamodb", region_name=config["AWS_REGION"])
    table = dynamodb.Table(config["AWS_DYNAMODB"])

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
    dynamodb = session.resource("dynamodb", region_name=config["AWS_REGION"])
    table = dynamodb.Table(config["AWS_DYNAMODB"])

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


# Initializing the messages queue to be used during the conversation
messages = get_dynamodb_messages()


# This function checks if the message was sent by the admin
def is_admin_message(message):
    # Comparing the user ID and the defined admin chat ID
    if message.chat.id != int(config["ADMIN_CHAT_ID"]):
        bot.send_message(
            message.chat.id, "Currently, only the admin has access to this feature."
        )
        return False
    return True


# Initial/welcome message handler
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        f"Hello, {message.chat.first_name}, welcome to the personal ChatGPT Telegram Chatbot!",
    )


# Command to clear current conversation
@bot.message_handler(commands=["clear"])
def clear_messages(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        # Clearing the current conversation
        clear_dynamo_messages()
        bot.reply_to(message, "Conversation was cleared!")


# Image generation request handler (future feature)
@bot.message_handler(commands=["image"])
# Image generation request handler (future feature)
def request_image(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        # Getting the text from the message
        text = message.text.strip()
        # If no content was provided
        if text == "/image":
            bot.send_message(
                message.chat.id,
                "Please provide a prompt for the image generation.",
            )
        # If a prompt was provided
        else:
            # We'll extract the prompt from the message text
            prompt = text.replace("/image", "")

            # If the content is too short
            if len(prompt) < 10:
                bot.send_message(
                    message.chat.id, "Prompt is too short (min length: 10 chars)."
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
                        message.chat.id,
                        photo=image_url,
                        caption=caption,
                    )
                # If something goes wrong, we'll inform about the error
                except Exception as e:
                    bot.send_message(
                        message.chat.id,
                        f"Error trying to generate the image: {e}",
                    )


# Visual input messages handler
@bot.message_handler(func=lambda msg: True, content_types=["photo"])
def visual_input(message):
    try:
        # Checking if a image caption was provided
        if message.caption is None:
            bot.send_message(
                message.chat.id,
                'Please, provide some context for the image as captions, e.g.: "What this image represents?"',
            )
            return

        # Getting the image path
        file_info = bot.get_file(message.photo[-1].file_id)

        # Creating the image URL for the photo
        image_url = f"https://api.telegram.org/file/bot{config['BOT_TOKEN']}/{file_info.file_path}"

        # Getting the image encoded as base64
        base64_image = url_to_base64(image_url)

        # If no image was returned
        if base64_image is None:
            bot.send_message(message.chat.id, "The image could not be retrieved.")
            return

        # Defining the headers for the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['OPENAI_API_KEY']}",
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
                        {"type": "text", "text": message.caption},
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
                message.chat.id, "There was an error while parsing the image."
            )
            return

        # Replying with the API response contet
        bot.send_message(
            message.chat.id, res.json()["choices"][0]["message"]["content"]
        )

        # Defining user message for the conversation
        user_message = {
            "role": "user",
            "content": message.caption,
        }
        # Defining bot response for the conversation
        bot_message = {
            "role": "assistant",
            "content": res.json()["choices"][0]["message"]["content"],
        }
        # Adding the newly received and generated messages to the list in order to provide to the chatbot
        messages.append(user_message)
        messages.append(bot_message)
        # Updating the DynamoDB table
        update_dynamo_messages(user_message)
        update_dynamo_messages(bot_message)

    # If something goes wrong
    except Exception as e:
        bot.send_message(
            message.chat.id, f"There was an error while processing your request: {e}"
        )


# General messages handler
@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        # Defining user message for the conversation
        user_message = {
            "role": "user",
            "content": message.text,
        }
        # Adding the newly received message to the messages list in order to provide to the chatbot
        messages.append(user_message)
        # Updating on the DynamoDB table
        update_dynamo_messages(user_message)

        # Making an API request to the chatbot
        res = openai.chat.completions.create(
            model=model_engine,
            messages=messages,
        )

        # Defining the response to be sent to the user
        user_response = res.choices[0].message.content
        # If desired, we can add the total tokens used on the request to the user
        user_response += f"\n\nTotal Tokens: {res.usage.total_tokens}"

        # Sending message back to the user
        bot.send_message(message.chat.id, user_response)

        # Defining bot response for the conversation
        bot_message = {
            "role": "assistant",
            "content": res.choices[0].message.content,
        }
        # We'll also append the bot response to the messages list and DynamoDB table
        # This will be used to update the conversation context
        messages.append(bot_message)
        update_dynamo_messages(bot_message)


# Here we can poll messages to test the chat locally
bot.infinity_polling()
