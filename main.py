from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import json
import os

app = FastAPI()

# Глобальна змінна для зберігання останніх даних у пам'яті
latest_data = None
# Список черг для сповіщення підключених веб-клієнтів
clients = []

@app.post("/api/push")
async def push_data(request: Request):
    global latest_data
    try:
        data = await request.json()
        
        # Атомарне оновлення посилання на дані
        latest_data = data
        
        # Сповіщаємо всі підключені веб-сторінки про оновлення
        for client_queue in clients:
            await client_queue.put("update")
            
        return {"success": True, "message": "Дані успішно оновлено"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Некоректний JSON")

@app.get("/api/get")
async def get_data():
    if latest_data is None:
        raise HTTPException(status_code=404, detail="Дані ще не надходили")
    return latest_data

# Ендпоінт для Server-Sent Events (Real-time оновлення для браузера)
@app.get("/api/events")
async def sse_endpoint(request: Request):
    client_queue = asyncio.Queue()
    clients.append(client_queue)

    async def event_generator():
        try:
            while True:
                # Якщо клієнт відключився, припиняємо генерацію
                if await request.is_disconnected():
                    break
                
                # Очікуємо сигнал про оновлення від POST /api/push
                message = await client_queue.get()
                yield f"data: {json.dumps({'type': message})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            clients.remove(client_queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Створюємо папку public, якщо її немає, і роздаємо статику
os.makedirs("public", exist_ok=True)
app.mount("/", StaticFiles(directory="public", html=True), name="public")

if __name__ == "__main__":
    # Запуск сервера
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
