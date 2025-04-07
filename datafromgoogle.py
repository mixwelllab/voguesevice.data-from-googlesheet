from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime
from difflib import get_close_matches

load_dotenv()

app = FastAPI()

TABLE_NAME = "vogue_clients_contacts"  # Название таблицы
SHEET_NAME = "list1"  # Название листа

# Модель запроса
class TopicRequest(BaseModel):
    topic: str
    count: int

# Авторизация через JSON в переменной окружения
def authorize_gsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise RuntimeError("❌ Переменная GOOGLE_CREDS_JSON не задана.")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# Загрузка данных таблицы
def load_table():
    client = authorize_gsheet()
    sheet = client.open(TABLE_NAME).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return sheet, data

# Поиск близкой рубрики
def find_best_rubric(requested_topic: str, all_rubrics: List[str]) -> str:
    matches = get_close_matches(requested_topic.lower(), [r.lower() for r in all_rubrics], n=1, cutoff=0.5)
    if not matches:
        return None
    matched = matches[0]
    for r in all_rubrics:
        if r.lower() == matched:
            return r
    return None

@app.get("/")
async def root():
    return {"message": "✅ Company API is working!"}

@app.get("/get_companies")
async def get_companies():
    _, data = load_table()
    issued = [row for row in data if str(row.get("was_issued", "")).strip().lower() == "true"]
    print(f"[INFO] Возвращено {len(issued)} ранее выданных компаний.")
    return {"companies": issued}

@app.post("/get_companies_by_topic")
async def get_companies_by_topic(request: TopicRequest):
    print(f"[START] Запрос от пользователя: {request.topic}, {request.count} компаний")

    sheet, data = load_table()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Собираем все рубрики
    rubrics = list(set([
        str(row.get("Рубрика", "")).strip()
        for row in data if row.get("Рубрика")
    ]))
    print(f"[DEBUG] Уникальные рубрики в таблице: {rubrics}")

    matched_rubric = find_best_rubric(request.topic, rubrics)
    print(f"[DEBUG] Найденная рубрика по запросу: {matched_rubric}")

    if not matched_rubric:
        print(f"[ERROR] Не удалось найти подходящую рубрику для темы '{request.topic}'")
        raise HTTPException(status_code=404, detail="Тематика не найдена в базе")

    # Фильтрация подходящих компаний
    available = [
        (i + 2, row)
        for i, row in enumerate(data)
        if str(row.get("Рубрика", "")).strip() == matched_rubric
        and str(row.get("was_issued", "")).strip().lower() != "true"
    ]
    print(f"[DEBUG] Найдено подходящих строк: {len(available)}")

    if not available:
        return {"companies": []}

    selected = available[:request.count]
    result = []

    for row_index, row in selected:
        result.append({
            "name": row.get("Название компании", "—"),
            "landline": row.get("Стационарный телефон компании", "—"),
            "mobile": row.get("Мобильный телефон компании", "—"),
            "toll_free": row.get("Бесплатный номер компании", "—"),
            "whatsapp": row.get("Whatsapp компании", "—"),
            "telegram": row.get("Telegram компании", "—"),
            "viber": row.get("Viber компании", "—"),
            "email": row.get("Email компании", "—"),
            "website": row.get("Сайт", "—"),
            "socials": row.get("Социальные сети", "—"),
            "title": row.get("Заголовок сайта (title)", "—"),
            "category": row.get("Рубрика", "—")
        })

        # Обновляем отметку о выдаче
        try:
            sheet.update_acell(f"X{row_index}", "TRUE")
            sheet.update_acell(f"Y{row_index}", today_str)
            print(f"[INFO] Строка {row_index} помечена как выданная.")
        except Exception as e:
            print(f"[ERROR] Не удалось обновить строку {row_index}: {e}")

    print(f"[SUCCESS] Возвращено {len(result)} компаний.")
    return {"companies": result}
