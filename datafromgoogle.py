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
SHEET_NAME = "list1"  # ⚠️ Убедись, что лист точно называется именно так в Google Sheets

# Модель запроса
class TopicRequest(BaseModel):
    topic: str
    count: int

# Авторизация в Google Sheets
def authorize_gsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json_str = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json_str:
        raise ValueError("⛔ Переменная окружения GOOGLE_CREDS_JSON не найдена")
    import json
    creds_dict = json.loads(creds_json_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# Получить таблицу и данные
def load_table():
    client = authorize_gsheet()
    spreadsheet = client.open(TABLE_NAME)
    all_sheets = [ws.title for ws in spreadsheet.worksheets()]
    print(f"[DEBUG] Листы в таблице: {all_sheets}")
    sheet = spreadsheet.worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return sheet, data

# Поиск ближайшей рубрики
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
    issued = [row for row in data if str(row.get("was_issued", "")).strip().lower() == "true_"]

