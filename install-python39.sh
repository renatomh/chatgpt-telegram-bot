#!/bin/bash

# AWS CloudShell script to install Python 3.9

sudo yum -y install gcc openssl-devel bzip2-devel libffi-devel
wget https://www.python.org/ftp/python/3.9.16/Python-3.9.16.tgz
tar zxf Python-3.9.16.tgz
cd Python-3.9.16/
./configure --enable-optimizations
sudo make altinstall
python3.9 --version
python3.9 -m pip install --upgrade pip
