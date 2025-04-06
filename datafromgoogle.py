from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

app = FastAPI()

# Получение переменных окружения
os.getenv("OPENAI_API_KEY")
os.getenv("GOOGLE_CREDS_JSON")
os.getenv("TABLE_NAME")

# Константа: название таблицы
TABLE_NAME = "vogue_clients_contacts"

# OpenAI клиент
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pydantic модели
class CompanyData(BaseModel):
    date: str
    name: str
    category: str
    offer: str

class CompaniesRequest(BaseModel):
    timestamp: str
    companies: List[CompanyData]

# Авторизация в Google Sheets
def authorize_gsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# Запись данных
def write_to_sheet(sheet_name: str, data: List[str]):
    client = authorize_gsheet()
    sheet = client.open(sheet_name).sheet1
    sheet.append_row(data)

# Чтение данных
def read_from_sheet(sheet_name: str):
    client = authorize_gsheet()
    sheet = client.open(sheet_name).sheet1
    return sheet.get_all_values()

# Роуты
@app.get("/")
async def root():
    return {"message": "Company Recorder API is working!"}

@app.get("/openai_test")
async def openai_test(prompt: str = "Привет!"):
    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"response": completion.choices[0].message.content}

@app.post("/save_companies")
async def save_companies(data: CompaniesRequest):
    for company in data.companies:
        row = [data.timestamp, company.date, company.name, company.category, company.offer]
        write_to_sheet(TABLE_NAME, row)
    return {"status": "success", "saved_companies": len(data.companies)}

@app.get("/get_companies")
async def get_companies():
    data = read_from_sheet(TABLE_NAME)
    return {"companies": data}
