# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import sys
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
)

# google
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# imgur
from imgurpython import ImgurClient

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

# get google sheet id from your environment variable
spread_sheet_id = os.getenv('GOOGLE_SHEET_ID', None)
if spread_sheet_id is None:
    print('Specify GOOGLE_SHEET_ID as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

@app.route("/", methods=['GET'])
def hello():
    return "Hello World!"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

def is_text_command(text):
    return text.startswith("!") or text.startswith("！")

def is_text_test_google(text):
    return text.startswith("!tgoogle")

def test_google_sheet_read():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SAMPLE_SPREADSHEET_ID = spread_sheet_id
    SAMPLE_RANGE_NAME = 'sheet1!A2:C'
    # use service_account to access google from other server
    # Reference: https://developers.google.com/identity/protocols/oauth2/service-account#python
    creds = service_account.Credentials.from_service_account_file(
            '../credentials.json', scopes=SCOPES)
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')
            return

        print('Name, Major:')
        for row in values:
            # Print columns A and E, which correspond to indices 0 and 4.
            print('%s, %s, %s' % (row[0], row[1], row[2]))
    except HttpError as err:
        print(err)

def command_respond(event, command, command_list):
    # find respond
    for row in command_list:
        command_type = row[2]
        if command_type == '1':
            # ignore command
            keywords = row[1].split(',')
            if command in keywords:
                return
        elif command_type == '2' or command_type == '-2':
            # text reply
            keywords = row[1].split(',')
            if command in keywords:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=row[0])
                )
                return
        elif command_type == '3' or command_type == '-3':
            # alias command
            keywords = row[1].split(',')
            if command in keywords:
                command_respond(event, row[0], command_list)
                return
        elif command_type == '4' or command_type == '-4':
            # upload imgur
            # pic reply
            keywords = row[1].split(',')
            if command in keywords:
                url = row[0]
                line_bot_api.reply_message(
                    event.reply_token,
                    ImageSendMessage(url, url)
                )
                return
        elif command_type == '5' or command_type == '-5':
            # command list
            keywords = row[1].split(',')
            if command in keywords:
                reply_text = ""
                for row2 in command_list:
                    if row2[2] == "2" or row2[2] == "4" or row2[2] == "5":
                        reply_text = reply_text + '\n' + row2[1]
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                return
        elif command_type == '6' or command_type == '-6':
            # pic reply
            keywords = row[1].split(',')
            if command in keywords:
                url = row[0]
                line_bot_api.reply_message(
                    event.reply_token,
                    ImageSendMessage(url, url)
                )
                return
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='command not found: ' + event.message.text)
    )

to_print_time_info = os.getenv('PRINT_TIME_INFO', None)
def command_parse(event, text):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SAMPLE_SPREADSHEET_ID = spread_sheet_id
    SAMPLE_RANGE_NAME = 'sheet1!A2:C'
    creds = service_account.Credentials.from_service_account_file(
                '../credentials.json', scopes=SCOPES)
    try:
        if to_print_time_info == "1":
            print('Build sheet service.', flush=True)
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        if to_print_time_info == "1":
            print('Spread sheet.', flush=True)
        sheet = service.spreadsheets()
        if to_print_time_info == "1":
            print('Get sheet.', flush=True)
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        if to_print_time_info == "1":
            print('Get value array.', flush=True)
        values = result.get('values', [])

        if not values:
            print('No data found.', flush=True)
            return

        if to_print_time_info == "1":
            print('Find command responce.', flush=True)
        command_respond(event, text.strip(), values)

    except HttpError as err:
        print(err)


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    if not is_text_command(event.message.text):
        return
    if is_text_test_google(event.message.text):
        test_google_sheet_read()
        return
    command_parse(event, event.message.text)

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)