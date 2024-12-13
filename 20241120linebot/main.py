from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    TemplateMessage,
    ButtonsTemplate,
    PostbackAction,
    PushMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent
import re
import requests
from dotenv import load_dotenv
import os

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

load_dotenv(".env")

user_info = {
    "user_id":None,
    "name": None,
    "idNumber": None,
    "tel": None,
    "step": 0  # 用來追蹤步驟，0 表示尚未開始，1 表示請輸入姓名，2 表示請輸入身分證字號，以此類推
}

access_token = os.getenv("ACCESS_TOKEN")
secret = os.getenv("SECRET")

configuration = Configuration(
    access_token=access_token)
handler = WebhookHandler(secret)

@app.route("/", methods=['POST'])
def linebot():

    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except Exception as e:
        app.logger.error(f"Error: {e}")

    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_info["user_id"] = event.source.user_id
        
        if event.message.text == "連結LINE集點":
            reply_text = "請輸入身分證字號"
            user_info["step"] = 1
            line_bot_api.reply_message_with_http_info(ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
            
        elif user_info["step"] == 1:
            idNumber = event.message.text
            lineId = event.source.user_id
            
            if re.match(r'^[A-Za-z]\d{9}$', idNumber):
                try:
                    response = requests.post(
                        url="https://linebotapi-tgkg.onrender.com/linkLineID/",
                        json={
                            "idNumber": idNumber,
                            "lineId": lineId
                        }
                    )
                    if response.status_code == 200:
                        reply_text = "連結成功"
                    else:
                        reply_text = "重複連結或錯誤，請確認!"
                except Exception as e:
                    print(f"Error during request: {e}")
                    reply_text = "請聯絡管理員"

                line_bot_api.reply_message_with_http_info(ReplyMessageRequest(
                    reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
                
                # 完成步驟後，重設步驟狀態（如果需要）
                user_info["step"] = 0  # 重設步驟為0
            else:
                reply_text = "身分證字號格式錯誤，請輸入有效的身分證字號（1個字母 + 9個數字）"
                line_bot_api.reply_message_with_http_info(ReplyMessageRequest(
                    reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))

        elif event.message.text == "集點":
            user_info["user_id"] = event.source.user_id
            print(event.source.user_id)
            response = requests.put(
                url="https://linebotapi-tgkg.onrender.com/add/healthMeasurement",
                json={
                    "lineId": user_info["user_id"]
                }  # 傳遞的 JSON 資料
            )
            print(response.status_code)
            data = response.json()
            health_measurement = data.get("healthMeasurement")  # 使用 .get() 確保鍵存在
            if response.status_code == 200:
                if(health_measurement < 15):
                    reply_text = f"集點完成，目前測量次數為{health_measurement}，加油!!"
                if(health_measurement == 15):
                    reply_text = f"集滿囉!!!可以拿給志工確認換禮物囉~"
                if(health_measurement > 15):
                    reply_text = "有持續量血壓很棒喔~"
                line_bot_api.reply_message_with_http_info(ReplyMessageRequest(
                    reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
            else:
                reply_text = "集點失敗！請稍後嘗試!"
                line_bot_api.reply_message_with_http_info(ReplyMessageRequest(
                    reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))

def main():
    port = int(os.getenv("PORT", 5000))  # 默認使用 5000，但優先使用環境變數 PORT
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()  # 呼叫 main() 函式啟動應用

@app.route("/trigger", methods=['GET', 'POST'])
def trigger_api():
    try:
        return "OKOK"
    except Exception as e:
        return "QQ"

# ngrok http http://127.0.0.1:5000
