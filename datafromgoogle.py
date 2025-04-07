@app.post("/get_companies_by_topic")
async def get_companies_by_topic(request: TopicRequest):
    sheet, data = load_table()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # === 🔍 Лог входящих данных
    print(f"[DEBUG] Получен запрос: topic='{request.topic}', count={request.count}")

    # Найдём все уникальные рубрики из таблицы
    rubrics = list(set([
        str(row.get("Рубрика", "")).strip()
        for row in data if row.get("Рубрика")
    ]))

    print(f"[DEBUG] Уникальные рубрики в таблице: {rubrics}")

    # Поиск наиболее близкой рубрики
    matched_rubric = find_best_rubric(request.topic, rubrics)
    print(f"[DEBUG] Найденная рубрика: {matched_rubric}")

    if not matched_rubric:
        print(f"[ERROR] Тематика '{request.topic}' не найдена среди рубрик.")
        raise HTTPException(status_code=404, detail="Тематика не найдена в базе")

    # Отбор подходящих компаний
    available = [
        (i + 2, row)
        for i, row in enumerate(data)
        if str(row.get("Рубрика", "")).strip() == matched_rubric
        and str(row.get("was_issued", "")).strip().lower() != "true"
    ]

    print(f"[DEBUG] Найдено подходящих компаний: {len(available)}")

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

        # ✅ Обновляем отметку в таблице
        sheet.update_acell(f"U{row_index}", "TRUE")
        sheet.update_acell(f"V{row_index}", today_str)

    print(f"[SUCCESS] Отправлено {len(result)} компаний в ответ.")
    return {"companies": result}
