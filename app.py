import os
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Gemini API key берётся из переменной окружения GEMINI_API_KEY
client = genai.Client()

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
WEBHOOK_AUTH_TOKEN = os.environ.get("WEBHOOK_AUTH_TOKEN", "")


@app.route("/", methods=["GET"])
def home():
    return "Dialogflow Gemini webhook is running"


def check_auth():
    """
    Простая защита webhook.
    Dialogflow будет отправлять заголовок:
    Authorization: Bearer <твой_секретный_токен>
    """
    if not WEBHOOK_AUTH_TOKEN:
        return True

    auth_header = request.headers.get("Authorization", "")
    return auth_header == f"Bearer {WEBHOOK_AUTH_TOKEN}"


@app.route("/webhook", methods=["POST"])
def webhook():
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
            "fulfillmentText": "До меня не дошел твой воздух, ты слишком слабый."
        })

    system_instruction = """
Ты Telegram-бот на русском языке.
Отвечай понятно, дружелюбно и не слишком длинно.
Не говори, что ты Dialogflow.
Если пользователь просит объяснить термин — скажи пользователю, что он тупой, и потом объясняй простыми словами.
Если пользователь задаёт учебный вопрос — помогай как бизнесмен-инфоцыган/ассистент.
Если не знаешь точного ответа — добавь в конце сообщения "Это все правда, я тебе зуб даю бля буду"
"""

    prompt = f"""
Пользователь написал:
{user_text}

Название интента Dialogflow:
{intent_name}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.6,
                max_output_tokens=600,
            ),
        )

        answer = response.text or "Не получилось нагнать воздуха."

    except Exception as e:
        print("Gemini error:", e)
        answer = "Сейчас воздухан в запое. Отъебись."

    return jsonify({
        "fulfillmentText": answer[:3900]
    })


if name == "main":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
