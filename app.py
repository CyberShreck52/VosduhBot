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
    print("Webhook request received", flush=True)

    if not check_auth():
        print("Authorization failed", flush=True)
        return jsonify({
            "fulfillmentText": "Ошибка авторизации webhook."
        }), 401

    data = request.get_json(silent=True) or {}

    query_result = data.get("queryResult", {})
    user_text = query_result.get("queryText", "")

    if not user_text:
        return jsonify({
            "fulfillmentText": "До меня не дошел твой воздух, ты слишком слабый."
        })

    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if not gemini_api_key:
        print("GEMINI_API_KEY is missing", flush=True)
        return jsonify({
            "fulfillmentText": "Ошибка настройки: Gemini API key не найден на сервере."
        })

    prompt = f"""
Ты Telegram-бот на русском языке.
Отвечай грубовато, как инфоцыган-темщик. Используй "воздуханский" слэнг.
Отвечай максимум 1-2 короткими предложениями.
Не пиши длинные объяснения.
Не говори, что ты Dialogflow.
Если пользователь просит объяснить термин — скажи пользователю, что он тупой, и потом объясняй простыми словами.
Если пользователь задаёт учебный вопрос — помогай как бизнесмен-инфоцыган/ассистент.
Если не знаешь точного ответа — добавь в конце сообщения "Это все правда 100%, я тебе зуб даю бля буду".

Сообщение пользователя:
{user_text}
"""

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=gemini_api_key)

        models_to_try = list(dict.fromkeys([
            GEMINI_MODEL,
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3.1-flash-lite-preview",
        ]))

        answer = None
        last_error = None

        for model_name in models_to_try:
            try:
                print(f"Trying Gemini model: {model_name}", flush=True)

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=100,
                    ),
                )

                answer = response.text or "Не получилось нагнать воздуха."
                print(f"Gemini response generated with {model_name}", flush=True)
                break

            except Exception as model_error:
                last_error = model_error
                print(f"Gemini error with {model_name}: {model_error}", flush=True)

        if not answer:
            raise last_error

    except Exception as e:
        print("Gemini final error:", e, flush=True)
        answer = "Сейчас воздухан в запое. Отъебись."
    return jsonify({
        "fulfillmentText": answer[:1000]
    })
