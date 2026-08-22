# Sequoia Server v0.4

إضافة الاعتمادية الذكية عند ضغط Gemini:

- إعادة المحاولة تلقائياً عند HTTP 429/500/502/503/504.
- ثلاث محاولات لكل نموذج مع انتظار متدرج.
- الانتقال تلقائياً إلى نماذج احتياطية إذا بقي النموذج الأساسي مشغولاً.
- النموذج الأساسي يأتي من GEMINI_MODEL.
- سلسلة الاحتياط الافتراضية:
  - gemini-3.6-flash
  - gemini-3.5-flash-lite
- يمكن تغييرها من Render بإضافة:
  GEMINI_FALLBACK_MODELS=gemini-3.6-flash,gemini-3.5-flash-lite
- استمرارية ذاكرة Supabase من v0.3.
- فشل استخراج الذاكرة لا يمنع وصول جواب المحادثة للمستخدم.

## Environment variables
Required:
- GEMINI_API_KEY
- GEMINI_MODEL
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- SEQUOIA_OWNER_ID

Optional:
- GEMINI_FALLBACK_MODELS
