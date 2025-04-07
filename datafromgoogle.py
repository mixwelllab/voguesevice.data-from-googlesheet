# === 🚀 FastAPI скрипт для работы с Google Таблицей: подбор и пометка компаний ===

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime
from difflib import get_close_matches

load_dotenv()

app = FastAPI()

TABLE_NAME = "vogue_clients_contacts"
SHEET_NAME = "list1"  # если у тебя другой лист — укажи точно

# Модель запроса на подбор компаний
class TopicRequest(BaseModel):
    topic: str
    count: int

# Авторизация в Google Sheets
def authorize_gsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)

# Прочитать таблицу и вернуть заголовки и данные
def load_table():
    client = authorize_gsheet()
    sheet = client.open(TABLE_NAME).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return sheet, data

# Найти наиболее подходящую рубрику
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
    return {"message": "Company API is working!"}

@app.get("/get_companies")
async def get_companies():
    _, data = load_table()
    issued = [row for row in data if str(row.get("was_issued", "")).strip().lower() == "true"]
    return {"companies": issued}

@app.post("/get_companies_by_topic")
async def get_companies_by_topic(request: TopicRequest):
    sheet, data = load_table()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Найдём все уникальные рубрики
    rubrics = list(set([row.get("Рубрика", "").strip() for row in data if row.get("Рубрика")]))
    matched_rubric = find_best_rubric(request.topic, rubrics)

    if not matched_rubric:
        raise HTTPException(status_code=404, detail="Тематика не найдена в базе")

    # Отбираем компании по рубрике и которые ещё не были выданы
    available = [
        (i + 2, row)  # +2 т.к. индекс в таблице начинается с 2 (после заголовков)
        for i, row in enumerate(data)
        if row.get("Рубрика", "").strip() == matched_rubric
        and str(row.get("was_issued", "")).strip().lower() != "true"
    ]

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

        # Записываем was_issued и дату
        sheet.update_acell(f"U{row_index}", "TRUE")  # U — колонка was_issued
        sheet.update_acell(f"V{row_index}", today_str)  # V — колонка issue_date

    return {"companies": result}
