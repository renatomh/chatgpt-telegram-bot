# -*- coding: utf-8 -*-
"""
Created on Mon Mar 13 11:50:00 2023

@author: Renato Henz

Telegram Chatbot server

"""

# Main dependencies
import telebot, openai, boto3
from dotenv import dotenv_values

# Getting the .env variables and keys
config = dotenv_values(".env")

# Instantiating the Telegram Chatbot object
bot = telebot.TeleBot(config['BOT_TOKEN'])

# Setting the API Key and model engine for OpenAI
openai.api_key = config['OPENAI_API_KEY']
model_engine = "gpt-3.5-turbo"

# Initializing the boto3 (AWS) session
session = boto3.Session(
    aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'],
)

# Function to get messages from DynamoDN table
def get_dynamodb_messages():
    # Initializing DynamoDB instance and getting table
    dynamodb = session.resource('dynamodb', region_name=config['AWS_REGION'])
    table = dynamodb.Table(config['AWS_DYNAMODB'])
    scan = table.scan()
    # Getting messages formatted as dict
    dynamo_messages = scan['Items'][0]['messages']
    
    # Returning resulting dict
    return dynamo_messages

# Function to update the messages list on DynamoDB table
def update_dynamo_messages(message):
    # Initializing DynamoDB instance and getting table
    dynamodb = session.resource('dynamodb', region_name=config['AWS_REGION'])
    table = dynamodb.Table(config['AWS_DYNAMODB'])
    
    # Getting the required item with the list of messages to be updated
    res = table.get_item(Key={'field': 'messages'})
    item = res['Item']
    
    # Appending the new message to the list
    # Must be formatted as one of the following:
    # {"role": "user", "content": "Text content'}
    # {"role": "assistant", "content": "Text content'}
    item['messages'].append(message)
    
    # Updating item in the table
    table.put_item(Item=item)

# Function to clear previous saved messages on DynamoDB table
def clear_dynamo_messages():
    # Initializing DynamoDB instance and getting table
    dynamodb = session.resource('dynamodb', region_name=config['AWS_REGION'])
    table = dynamodb.Table(config['AWS_DYNAMODB'])
    
    # Getting the required item with the list of messages to be updated
    res = table.get_item(Key={'field': 'messages'})
    item = res['Item']
    
    # Clearing the list of items
    item['messages'] = []
    
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
    if message.chat.id != int(config['ADMIN_CHAT_ID']):
        bot.send_message(message.chat.id, "Currently, only the admin has access to this feature.")
        return False
    return True

# Initial/welcome message handler
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"Hello, {message.chat.first_name}, welcome to the personal ChatGPT Telegram Chatbot!")

# Command to clear current conversation
@bot.message_handler(commands=['clear'])
def clear_messages(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        # Clearing the current conversation
        clear_dynamo_messages()
        bot.reply_to(message, "Conversation was cleared!")

# Image generation request handler (future feature)
@bot.message_handler(commands=['image'])
def request_image(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        bot.reply_to(message, "This feature is not available yet.")

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
        res = openai.ChatCompletion.create(
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
