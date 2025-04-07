from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime
from difflib import get_close_matches
import json

load_dotenv()

app = FastAPI()

TABLE_NAME = "vogue_clients_contacts"
SHEET_NAME = "list1"

class TopicRequest(BaseModel):
    topic: str
    count: int

def authorize_gsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json_str = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json_str:
        raise ValueError("⛔ Переменная окружения GOOGLE_CREDS_JSON не найдена")
    creds_dict = json.loads(creds_json_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def load_table():
    client = authorize_gsheet()
    spreadsheet = client.open(TABLE_NAME)
    all_sheets = [ws.title for ws in spreadsheet.worksheets()]
    print(f"[DEBUG] Листы в таблице: {all_sheets}")
    sheet = spreadsheet.worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return sheet, data

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
async def get_companies(month: int = None, year: int = None):
    try:
        sheet, data = load_table()
        filtered = []
        for row in data:
            if str(row.get("was_issued", "")).strip().lower() != "true":
                continue
            issue_date = row.get("issue_date", "")
            if month and year:
                target_prefix = f"{year}-{month:02d}"
                if not issue_date.startswith(target_prefix):
                    continue
            filtered.append([
                row.get("index", ""),
                issue_date,
                row.get("Название компании", ""),
                row.get("Рубрика", ""),
                row.get("Офер", "")
            ])
        return {"companies": filtered}
    except Exception as e:
        print(f"[ERROR] Ошибка при получении компаний: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
        
@app.post("/get_companies_by_topic")
async def get_companies_by_topic(req: TopicRequest):
    try:
        sheet, data = load_table()

        all_rubrics = list(set(row.get("Рубрика", "") for row in data))
        best_rubric = find_best_rubric(req.topic, all_rubrics)

        if not best_rubric:
            return {"companies": []}

        matched = [row for row in data if row.get("Рубрика", "").strip().lower() == best_rubric.strip().lower() and str(row.get("was_issued", "")).strip().lower() != "true"]

        result = []
        now = datetime.now()
        for row in matched[:req.count]:
            result.append({
                "index": row.get("index", ""),
                "name": row.get("Название компании", ""),
                "category": row.get("Рубрика", ""),
                "website": row.get("website", "—"),
                "email": row.get("email", "—"),
                "landline": row.get("landline", "—"),
                "mobile": row.get("mobile", "—"),
                "toll_free": row.get("toll_free", "—"),
                "whatsapp": row.get("whatsapp", "—"),
                "telegram": row.get("telegram", "—"),
                "viber": row.get("viber", "—"),
                "socials": row.get("socials", []),
                "title": row.get("title", "—"),
                "offer": row.get("Офер", "—"),
            })

            row_num = int(row.get("index")) + 2
            sheet.update_acell(f"X{row_num}", "TRUE")
            sheet.update_acell(f"Y{row_num}", now.strftime("%Y-%m-%d"))

        return {"companies": result}

    except Exception as e:
        print(f"[ERROR] Ошибка в get_companies_by_topic: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обработке запроса")
