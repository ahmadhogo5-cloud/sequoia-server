
# Sequoia AI Server

السيرفر الأولي لتطبيق Sequoia Android.

## المتغيرات المطلوبة على Render
- `GEMINI_API_KEY` = مفتاح Gemini API من Google AI Studio
- `GEMINI_MODEL` = `gemini-3.7-flash`

## أوامر Render
Build:
`pip install -r requirements.txt`

Start:
`uvicorn main:app --host 0.0.0.0 --port $PORT`

## اختبار السيرفر
- `/health`
- POST `/chat`

مثال JSON:
```json
{
  "user_id": "user-1",
  "message": "مرحبا سيكويا",
  "relationship": "رفيق يومي",
  "dialect": "شامي",
  "history": []
}
```

ملاحظة: الذاكرة الدائمة والصوت والفيديو ستضاف في المراحل التالية.
