<h1 align="center"><img alt="ChatGPT Telegram Bot" title="ChatGPT Telegram Bot" src=".github/logo.png" width="250" /></h1>

# ChatGPT Telegram Bot

## 💡 Project's Idea

This project was developed to provide a personal Telegram Chatbot that allows communication with OpenAI's ChatGPT API. It aims to be deployed with AWS Lambda functions, in order to make it scalable.

[Access it live on Telegram](https://t.me/personal_telegram_chatgpt_bot) (only available for the admin, in order to avoid API costs to the owner. You can create your own, using this code as base)

## 🔍 Features

* Ask ChatGPT specific questions;
* Have context based conversations with ChatGPT;

<p align="center">
    <img src=".github/sample.gif" alt="sample" />&emsp;
</p>

## 🛠 Technologies

During the development of this project, the following techologies were used:

- [Python](https://www.python.org/)
- [Telegram Bots](https://core.telegram.org/bots)
- [AWS Lambda](https://aws.amazon.com/pt/lambda/)
- [AWS DynamoDB](https://aws.amazon.com/pt/dynamodb/)
- [Amazon API Gateway](https://aws.amazon.com/pt/api-gateway/)
- [ChatGPT API](https://openai.com/blog/introducing-chatgpt-and-whisper-apis)

## 💻 Project Configuration

### First, create a new virtual environment on the root directory

```bash
$ python -m venv env
```

### Activate the created virtual environment

```bash
$ .\env\Scripts\activate # On Windows machines
$ source ./env/bin/activate # On MacOS/Unix machines
```

### Install the required packages/libs

```bash
(env) $ pip install -r requirements.txt
```

## 🌐 Setting up config files

Create an *.env* file on the root directory, with all needed variables, credentials and API keys, according to the sample provided (*example.env*).

## ⏯️ Running

To run the project in a development environment, execute the following command on the root directory, with the virtual environment activated.

```bash
(env) $ python bot.py
```

In order to leave the virtual environment, you can simply execute the command below:

```bash
(env) $ deactivate
```

### 👀 Observations

If you want to deploy the bot with AWS Lambda functions, the code file will be the [lambda function file](./lambda_function.py).

For that, there are some extra steps to be done, such as:

1. Creating the AWS Lambda function;
2. Setting the function trigger as an Amazon API Gateway;
3. Setting the webhook for the Telegram communication with the API Gateway route;
4. Creating the DynamoDB file with the messages list;
5. Adjusting the AWS Lambda function role to allow accessing the DynamoDB tables;
6. Setting up environment variables on the configurations for the Lambda function;
7. Adding the external Python libraries to Lambda function using layers;

### Documentation:
* [Telegram Bot API](https://core.telegram.org/bots/api)
* [Building a Scalable Telegram Chatbot with Python and Serverless Function.](https://awstip.com/building-a-scalable-telegram-chatbot-with-python-and-serverless-function-eed20902ac1f)
* [telegram.ext package](https://python-telegram-bot.readthedocs.io/en/stable/telegram.ext.html)
* [Add External Python Libraries to AWS Lambda using Lambda Layers](https://www.linkedin.com/pulse/add-external-python-libraries-aws-lambda-using-layers-gabe-olokun/)

## 📄 License

This project is under the **MIT** license. For more information, access [LICENSE](./LICENSE).
