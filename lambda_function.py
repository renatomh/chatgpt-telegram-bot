# Function dependencies
import json, os
import telebot
import openai
import logging
import boto3

# Setting up the loggers
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initializing the Bot
bot = telebot.TeleBot(os.environ['BOT_TOKEN'])

# Setting the API Key and model engine for OpenAI
openai.api_key = os.environ['OPENAI_API_KEY']
model_engine = "gpt-3.5-turbo"

# This function checks if the message was sent by the admin
def is_admin_message(message):
    # Comparing the user ID and the defined admin chat ID
    if message['chat']['id'] != int(os.environ['ADMIN_CHAT_ID']):
        bot.send_message(
            message['chat']['id'],
            "Currently, only the admin has access to this feature.",
        )
        return False
    return True

# Function to get messages from DynamoDN table
def get_dynamodb_messages():
    # Initializing DynamoDB instance and getting table
    dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])
    table = dynamodb.Table(os.environ['AWS_DYNAMODB'])
    scan = table.scan()
    # Getting messages formatted as dict
    dynamo_messages = scan['Items'][0]['messages']
    
    # Returning resulting dict
    return dynamo_messages

# Function to update the messages list on DynamoDB table
def update_dynamo_messages(message):
    # Initializing DynamoDB instance and getting table
    dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])
    table = dynamodb.Table(os.environ['AWS_DYNAMODB'])
    
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
    dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])
    table = dynamodb.Table(os.environ['AWS_DYNAMODB'])
    
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

# Initial/welcome message handler
def send_welcome(message):
    bot.send_message(
        message['chat']['id'], 
        f"Hello, {message['chat']['first_name']}, welcome to the personal ChatGPT Telegram Chatbot!"
    )

# Command to clear current conversation
def clear_messages(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        # Clearing the current conversation
        clear_dynamo_messages()
        bot.send_message(
            message['chat']['id'],
            "Conversation was cleared!"
        )

# Image generation request handler (future feature)
def request_image(message):
    # Checking if it's an admin message
    if is_admin_message(message):
        bot.send_message(
            message['chat']['id'],
            "This feature is not available yet."
        )

# Main function
def lambda_handler(event, context):
    try:
        # Getting the message from the event
        message = json.loads(event['body'])['message']
        
        # Split between three variables bellow
        
        # Chat ID will guide your chatbot reply
        chat_id = message['chat']['id']
        # Sender's first name, registered by user's Telegram app
        sender = message['from']['first_name']
        # The message content
        text = message['text']
        
        # Logging data about message received
        logger.info(sender)
        logger.info(text)
        
        # If user is sending an available command
        if text in ['/start', '/clear', '/image']:
            if text == '/start': send_welcome(message)
            elif text == '/clear': clear_messages(message)
            elif text == '/image': request_image(message)
            return
        
        # Otherwise, we'll save the message to the DynamoDB table
        update_dynamo_messages({
            'role': 'user',
            'content': text
        })
        
        # Here, we'll talk to ChatGPT
        
        # First, we get the messages list
        messages = get_dynamodb_messages()
        # Making an API request to the OpenAI API
        res = openai.ChatCompletion.create(
            model=model_engine,
            messages=messages,
        )
        
        # Defining the response to be sent to the user
        response = res.choices[0].message.content
        # We'll also save the response to the DynamoDB table
        update_dynamo_messages({
            'role': 'assistant',
            'content': response
        })
        
        # If desired, we can add the total tokens used on the request to the user
        response += f"\n\nTotal Tokens: {res.usage.total_tokens}"
        
        # Finally, we'll reply the user's message
        bot.send_message(chat_id, response)
    
    # If something goes wrong
    except Exception as e:
        # We'll just log the error
        logger.error(e)
