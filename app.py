import os
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
WEBHOOK_AUTH_TOKEN = os.environ.get("WEBHOOK_AUTH_TOKEN", "")


@app.route("/", methods=["GET"])
def home():
    return "Dialogflow Gemini webhook is running"


@app.route("/webhook", methods=["GET"])
def webhook_get():
    return "Webhook endpoint is working. Dialogflow should send POST requests here."


def check_auth():
    if not WEBHOOK_AUTH_TOKEN:
        return True

    auth_header = request.headers.get("Authorization", "")
    return auth_header == f"Bearer {WEBHOOK_AUTH_TOKEN}"


@app.route("/webhook", methods=["POST"])
def webhook_post():
    if not check_auth():
        return jsonify({
            "fulfillmentText": "Ошибка авторизации webhook."
        }), 401

    data = request.get_json(silent=True) or {}

    query_result = data.get("queryResult", {})
    user_text = query_result.get("queryText", "")
    intent_name = query_result.get("intent", {}).get("displayName", "")

    if not user_text:
        return jsonify({
            "fulfillmentText": "Я не получил текст сообщения."
        })

    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if not gemini_api_key:
        return jsonify({
            "fulfillmentText": "Ошибка настройки: Gemini API key не найден на сервере."
        })

    prompt = f"""
Ты Telegram-бот на русском языке.
Отвечай понятно, дружелюбно и не слишком длинно.
Не говори, что ты Dialogflow.
Если пользователь просит объяснить термин — объясняй простыми словами.
Если пользователь задаёт учебный вопрос — помогай как ассистент.
Если не знаешь точного ответа — честно скажи, что не уверен.

Сообщение пользователя:
{user_text}

Название интента Dialogflow:
{intent_name}
"""

    try:
        from google import genai

        client = genai.Client(api_key=gemini_api_key)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        answer = response.text or "Не получилось сгенерировать ответ."

    except Exception as e:
        print("Gemini error:", e)
        answer = "Воздухан сейчас занят, попробуй позже."

    return jsonify({
        "fulfillmentText": answer[:3900]
    })
