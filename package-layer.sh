#!/bin/bash

# AWS CloudShell script to package dependencies from a local "requirements.txt" file and upload to s3

python3.9 -m pip install -r requirements.txt -t python/
zip -r python-chatgpt.zip python/
aws s3 cp python-chatgpt.zip s3://chatgpt-telegram-bot/
rm python-chatgpt.zip
