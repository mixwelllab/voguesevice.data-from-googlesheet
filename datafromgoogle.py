#АЛГОРИТМ РАБОТЫ СКРИПТА. для скрипта нужно создавать FAST API сервер через uvicorn
#для работы скрипта используется гугл таблица доступная через апи через
 #console.cloud.google.com/apis/credentials, был скачан и получен файл credentials
 # credentials.json и для созданной гугл таблицы vogue_clients_contacts дал доступ для этого
 # credentials, тесты работы можно проводить через постман 

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Константа: название таблицы — замени на СВОЁ точное название!
TABLE_NAME = "vogue_clients_contacts"  # <-- замени на своё название таблицы

# OpenAI клиент
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pydantic модель
class CompaniesList(BaseModel):
    companies: List[str]

# Авторизация в Google Sheets
def authorize_gsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")  # credentials.json
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
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
async def save_companies(companies_list: CompaniesList):
    write_to_sheet(TABLE_NAME, companies_list.companies)
    return {"status": "success", "saved_companies": companies_list.companies}

@app.get("/get_companies")
async def get_companies():
    data = read_from_sheet(TABLE_NAME)
    return {"companies": data}
