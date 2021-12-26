import boto3
import datetime
import json
import os
import urllib.request
from linebot import (LineBotApi, WebhookHandler)
from linebot.models import (MessageEvent, TextMessage, TextSendMessage)
from linebot.exceptions import (LineBotApiError, InvalidSignatureError)

from logging import getLogger, StreamHandler, DEBUG
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

SSM_PATH_NAME = os.environ['SSM_PATH_NAME']
ENV_NAME = os.environ['ENV_NAME']
SSM_PATH = '/' + SSM_PATH_NAME + '/' + ENV_NAME

LINE_CHANNEL_ACCESS_TOKEN = ''
DYNAMO_TABLE_NAME = ''
DEFAULT_AMOUNT = ''
GOAL_AMOUNT = ''

dynamodb = boto3.client('dynamodb')

def handler(event, context):
    logger.info('event: {}'.format(event))

    try:
        logger.info('getting secrets...')
        response = get_ssm_parameters()
        logger.info(response)
    except Exception as err:
        logger.info('getting secrets failed.')
        logger.error(err)
        return

    reply_url = 'https://api.line.me/v2/bot/message/reply'
    reply_headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + LINE_CHANNEL_ACCESS_TOKEN
    }

    request = json.loads(event['body'])['events'][0]
    reply_token = request['replyToken']
    message_text = request['message']['text']

    ## 文字数6文字で数値ならdynamodb書き込み -> put record succeeded. / put record failed.
    ## 文字数6文字 + del なら該当レコード削除 -> delete record succeeded. / delete record failed.
    ## それ以外は残数返信 -> total amount - total left. / get left amount faled.
    #### reply_message = ''（not reply_message） の時に稼働？
    reply_message = ''

    if message_text.isnumeric() and len(message_text) == 6:
        target_year = message_text[:4]
        target_month = message_text[4:]

        # dynamodbにレコード登録
        try:
            response = register_to_dynamo_db(target_year, target_month)

            success_message = 'put item succeeded.'
            logger.info(success_message)
            reply_message = success_message

        except Exception as err:
            failure_message = 'put item faled.'
            logger.info(failure_message)
            reply_message = failure_message

    else:
        # 残数計算
        try:
            left_amount = get_left_amount()

            success_message = 'get left amount succeeded.'
            logger.info(success_message)
            reply_message = str(left_amount) + ' left.'

        except Exception as err:
            failure_message = 'get left amount faled.'
            logger.info(failure_message)
            reply_message = failure_message

    body = {
        'replyToken': reply_token,
        'messages': [
            {
                "type": "text",
                "text": reply_message
            }
        ]
    }
    message_request = urllib.request.Request(
        reply_url,
        method = 'POST',
        headers = reply_headers,
        data = json.dumps(body).encode('utf-8')
    )

    try:
        with urllib.request.urlopen(message_request) as response:
            logger.info(response.read().decode("utf-8"))
    except Exception as err:
        logger.info('reply message failed.')
        logger.error(str(err))
        raise Exception(str(err))

# dynamodbにレコード登録
def register_to_dynamo_db(target_year, target_month):
    timezone_jst = datetime.timezone(datetime.timedelta(hours=9))
    time_stamp = datetime.datetime.now(timezone_jst).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    item = {
        'year': {'N': str(target_year)},
        'month': {'N': str(target_month)},
        'amount': {'N': DEFAULT_AMOUNT},
        'created_at': {'S': time_stamp}
    }

    try:
        response = dynamodb.put_item(
            TableName = DYNAMO_TABLE_NAME,
            Item = item
        )
        logger.info('register dynamodb succeeded.')
        logger.info(response)

        return

    except Exception as err:
        logger.info('register dynamodb failed.')
        logger.error('error', str(err))
        raise Exception(str(err))

# 残数計算
def get_left_amount():
    # dynamodbからレコード全数取得
    try:
        response = dynamodb.scan(TableName = DYNAMO_TABLE_NAME)
        records = response['Items']

    except Exception as err:
        logger.info('scan dynamodb failed.')
        logger.error('error', str(err))
        raise Exception(str(err))

    # レスポンスに LastEvaluatedKey が含まれなくなるまでループ
    while 'LastEvaluatedKey' in response:
        last_evaluated_key = response['LastEvaluatedKey']

        try:
            response = dynamodb.scan(
                TableName = DYNAMO_TABLE_NAME,
                ExclusiveStartKey = last_evaluated_key
            )

        except Exception as err:
            logger.info('scan dynamodb failed.')
            logger.error('error', str(err))
            raise Exception(str(err))

        if 'LastEvaluatedKey' in response:
            logger.info('LastEvaluatedKey: {}'.format(response['LastEvaluatedKey']))

        records.extend(response['Items'])

    logger.info('records: {}'.format(records))

    sum_amount = 0
    for record in records:
        sum_amount += int(record['amount']['N'])

    left_amount = int(GOAL_AMOUNT) - int(sum_amount)

    return left_amount

def get_ssm_parameters():
    ssm = boto3.client('ssm')

    params = dict()
    body = ssm.get_parameters_by_path(
            Path = SSM_PATH,
            WithDecryption = True
        )

    for param in body['Parameters']:
        key = param['Name'].replace(SSM_PATH + '/', '')
        params[key] = param['Value']

    while True:
        if not 'NextToken' in body:
            break

        body = ssm.get_parameters_by_path(
            Path = SSM_PATH,
            WithDecryption = True,
            NextToken = body['NextToken']
        )

        for param in body['Parameters']:
            key = param['Name'].replace(SSM_PATH + '/', '')
            params[key] = param['Value']

    global LINE_CHANNEL_ACCESS_TOKEN; LINE_CHANNEL_ACCESS_TOKEN = params['LINE_CHANNEL_ACCESS_TOKEN']
    global DYNAMO_TABLE_NAME; DYNAMO_TABLE_NAME = params['DYNAMO_TABLE_NAME']
    global DEFAULT_AMOUNT; DEFAULT_AMOUNT = params['DEFAULT_AMOUNT']
    global GOAL_AMOUNT; GOAL_AMOUNT = params['GOAL_AMOUNT']

    return 'getting secrets succeeded.'
