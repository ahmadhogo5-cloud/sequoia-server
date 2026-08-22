# Sequoia Server v0.3 — Persistent Memory

تضيف هذه النسخة:
- حفظ كل رسائل المستخدم والمساعد في Supabase.
- استرجاع آخر المحادثات قبل كل رد.
- استخراج ذكريات طويلة الأمد تلقائياً.
- فحص الذاكرة عبر `/memory/status`.

Environment variables المطلوبة:
- GEMINI_API_KEY
- GEMINI_MODEL
- PYTHON_VERSION
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- SEQUOIA_OWNER_ID

ملاحظة: يمكن وضع Supabase Secret key الحديث داخل المتغير SUPABASE_SERVICE_ROLE_KEY. يبقى المفتاح في Render فقط ولا يوضع داخل APK.
