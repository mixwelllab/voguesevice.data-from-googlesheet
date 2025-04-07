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
