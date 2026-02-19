import streamlit as st
import pandas as pd
import json
import time
import io
import re
import openpyxl
import asyncio
import aiohttp

# ══════════════════════════════════════════════════════════════
#  مولّد أوصاف عطور احترافي (النسخة الصاروخية Asynchronous)
#  متوافق مع سلة 100% | معالجة متزامنة | إعادة محاولة ذكية
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="مولّد أوصاف عطور SEO | أسرع أداء",
    page_icon="⚡",
    layout="wide",
)

# ─── CSS لتحسين الواجهة ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
*{font-family:'Tajawal',sans-serif}
[data-testid="stAppViewContainer"]{direction:rtl;text-align:right}
[data-testid="stSidebar"]{direction:rtl;text-align:right}
h1{text-align:center!important;background:linear-gradient(135deg,#d4af37,#b8960c);
   -webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.2rem!important}
.stButton>button{
    background:linear-gradient(135deg,#d4af37,#b8960c);
    color:#fff;border:none;border-radius:12px;
    padding:16px 30px;font-size:20px;font-weight:700;width:100%;
    box-shadow:0 4px 15px rgba(212,175,55,.3);transition:all .3s ease;
}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(212,175,55,.4)}
.product-item{
    background:#fafafa;border-left:4px solid #d4af37;
    border-radius:8px;padding:10px 16px;margin:5px 0;font-size:14px
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───
API_URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    "Google Gemini 2.0 Flash": "google/gemini-2.0-flash-001",
    "Google Gemini Flash 1.5": "google/gemini-flash-1.5",
    "GPT-4o Mini": "openai/gpt-4o-mini",
}

# ─── Helper Functions ───
def is_empty(val) -> bool:
    if pd.isna(val):
        return True
    s = str(val).strip()
    return s in ("", "nan", "<p></p>", "<p><br></p>", "None", "<p> </p>")

def get_api_provider(api_key: str) -> str:
    if api_key.startswith("AIza"):
        return "google"
    return "openrouter"

# ─── Asynchronous Core ───
async def fetch_notes_async(session, name: str, api_key: str, model: str, store_name: str, provider: str, semaphore):
    """جلب المعلومات بسرعة صاروخية مع نظام إعادة المحاولة عند الفشل"""
    
    system_msg = """أنت خبير محتوى وتسويق إلكتروني متخصص في العطور الفاخرة.
مهمتك: كتابة محتوى تسويقي احترافي، دقيق بناءً على Fragrantica، وطويل جداً (أكثر من 2000 حرف).
أرجع النتيجة بصيغة JSON فقط وبدون أي نص إضافي:
{
  "perfume_en": "الاسم الإنجليزي الكامل",
  "perfume_ar": "الاسم العربي الكامل",
  "type": "نوع العطر",
  "concentration": "التركيز",
  "family": "العائلة العطرية",
  "perfumer": "اسم العطار الحقيقي",
  "year": "سنة الإصدار",
  "intro_paragraph": "مقدمة تسويقية إبداعية وسردية طويلة جداً.",
  "top_notes": "وصف طويل للنوتات العليا",
  "heart_notes": "وصف طويل للنوتات الوسطى",
  "base_notes": "وصف طويل للنوتات الأساسية ومدى ثباتها",
  "general_vibe": "الطابع العام للعطر في جملتين",
  "why_choose_1": "سبب أول قوي مع شرح",
  "why_choose_2": "سبب ثاني مع تفصيل",
  "why_choose_3": "سبب ثالث مع تفصيل",
  "faq_1_q": "سؤال شائع 1", "faq_1_a": "إجابة 1",
  "faq_2_q": "سؤال شائع 2", "faq_2_a": "إجابة 2",
  "faq_3_q": "سؤال شائع 3", "faq_3_a": "إجابة 3",
  "closing_paragraph": "خاتمة طويلة وجذابة"
}"""

    user_msg = f'اكتب وصفاً احترافياً مطولاً (أكثر من 2000 حرف) للمنتج: "{name}" لمتجر "{store_name}".'

    # استخدام إشارة المرور (Semaphore) لمنع إغراق السيرفرات بالطلبات دفعة واحدة
    async with semaphore:
        # نظام إعادة المحاولة (يُحاول 3 مرات كحد أقصى)
        for attempt in range(3):
            try:
                if provider == "google":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                    headers = {"Content-Type": "application/json"}
                    body = {
                        "contents": [{"role": "user", "parts": [{"text": system_msg + "\n\n" + user_msg}]}],
                        "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}
                    }
                    async with session.post(url, headers=headers, json=body) as response:
                        if response.status != 200:
                            await asyncio.sleep(2 ** attempt) # انتظار تصاعدي قبل المحاولة القادمة
                            continue
                        res_json = await response.json()
                        text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                else: # OpenRouter
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://perfume-desc-generator.streamlit.app",
                    }
                    body = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg},
                        ],
                        "temperature": 0.4, "max_tokens": 3000,
                    }
                    async with session.post(API_URL_OPENROUTER, headers=headers, json=body) as response:
                        if response.status != 200:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        res_json = await response.json()
                        text = res_json["choices"][0]["message"]["content"].strip()

                # استخراج JSON وتجاهل الأخطاء النصية
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    parsed_data = json.loads(match.group(0))
                    if isinstance(parsed_data, dict):
                        return parsed_data
            
            except Exception as e:
                await asyncio.sleep(2 ** attempt)
                
        return None # إذا فشلت كل المحاولات

def build_html_salla(name: str, d: dict, store_name: str, store_link: str) -> str:
    """بناء HTML وتصفيته من الفراغات والأسطر الجديدة كلياً"""
    a_tag = f'<a href="{store_link}" style="color: #d4af37; font-weight: bold; text-decoration: none;">{store_name}</a>' if store_name and store_link else f'<strong style="color: #d4af37;">{store_name}</strong>'
    m = re.search(r"(\d+)\s*مل", name)
    size = m.group(0) if m else "حسب الاختيار المتاح"

    html = f"""
<div style="font-family: 'Tajawal', 'Arial', sans-serif; color: #333; line-height: 1.8; text-align: right; direction: rtl;">
<p style="margin-bottom: 15px;">{d.get('intro_paragraph', '')} يقدم لك {a_tag} هذا العطر الفاخر لتكتمل أناقتك.</p>

<h2 style="background-color: #f9f9f9; border-right: 5px solid #d4af37; padding: 12px 15px; font-size: 20px; color: #333; margin-top: 25px; margin-bottom: 15px; border-radius: 4px;">تفاصيل المنتج</h2>
<ul style="padding-right: 20px; margin-bottom: 15px;">
  <li style="margin-bottom: 8px;"><strong>الاسم:</strong> {d.get('perfume_ar', name)} ({d.get('perfume_en', '')})</li>
  <li style="margin-bottom: 8px;"><strong>السعة:</strong> {size}</li>
  <li style="margin-bottom: 8px;"><strong>نوع المنتج:</strong> {d.get('type', 'عطر')}</li>
  <li style="margin-bottom: 8px;"><strong>التركيز:</strong> {d.get('concentration', '')}</li>
  <li style="margin-bottom: 8px;"><strong>العائلة العطرية:</strong> {d.get('family', '')}</li>
  <li style="margin-bottom: 8px;"><strong>العطّار:</strong> {d.get('perfumer', '')}</li>
  <li style="margin-bottom: 8px;"><strong>سنة الإصدار:</strong> {d.get('year', '')}</li>
  <li style="margin-bottom: 8px;"><strong>متوفر عبر:</strong> {a_tag}، وجهتك المثالية لكل ما يتعلق بالعطور الفاخرة</li>
</ul>

<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 15px; margin-bottom: 10px; display: inline-block;">رحلة العطر - النفحات والمكونات</h3>
<ul style="padding-right: 20px; margin-bottom: 15px;">
  <li style="margin-bottom: 8px;"><strong>النوتات العليا:</strong> {d.get('top_notes', '')}</li>
  <li style="margin-bottom: 8px;"><strong>النوتات الوسطى:</strong> {d.get('heart_notes', '')}</li>
  <li style="margin-bottom: 8px;"><strong>النوتات الأساسية:</strong> {d.get('base_notes', '')}</li>
  <li style="margin-bottom: 8px;"><strong>الطابع العام:</strong> {d.get('general_vibe', '')}</li>
</ul>

<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 15px; margin-bottom: 10px; display: inline-block;">لماذا تختار هذا العطر؟</h3>
<ul style="padding-right: 20px; margin-bottom: 15px;">
  <li style="margin-bottom: 8px;"><strong>تميز وانفراد:</strong> {d.get('why_choose_1', '')}</li>
  <li style="margin-bottom: 8px;"><strong>جودة وثبات:</strong> {d.get('why_choose_2', '')}</li>
  <li style="margin-bottom: 8px;"><strong>تعدد المناسبات:</strong> {d.get('why_choose_3', '')}</li>
  <li style="margin-bottom: 8px;"><strong>متوفر حصرياً في:</strong> {a_tag} حيث نضمن لك الأصالة 100% وأفضل الأسعار مع خدمة توصيل سريعة.</li>
</ul>

<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 15px; margin-bottom: 10px; display: inline-block;">الأسئلة الشائعة</h3>
<ul style="padding-right: 20px; margin-bottom: 15px;">
  <li style="margin-bottom: 8px;"><strong>{d.get('faq_1_q', 'هل العطر مناسب للاستخدام اليومي؟')}</strong><br>{d.get('faq_1_a', '')}</li>
  <li style="margin-bottom: 8px;"><strong>{d.get('faq_2_q', 'هل يناسب فصل معين؟')}</strong><br>{d.get('faq_2_a', '')}</li>
  <li style="margin-bottom: 8px;"><strong>{d.get('faq_3_q', 'ما مدى ثبات العطر على الجلد؟')}</strong><br>{d.get('faq_3_a', '')}</li>
  <li style="margin-bottom: 8px;"><strong>هل المنتج أصلي؟</strong><br>نعم، جميع منتجات {a_tag} أصلية 100% مع ضمان ذهبي للأصالة والجودة.</li>
</ul>

<p style="margin-bottom: 15px;">{d.get('closing_paragraph', '')} اختر التميز، اختر {a_tag}.</p>
</div>
"""
    # تنظيف صارم 100% للأسطر الجديدة والمسافات الزائدة
    html_clean = html.replace("\n", "").replace("\r", "")
    html_clean = re.sub(r'\s{2,}', ' ', html_clean)
    return html_clean

async def process_product(session, row_i, pname, active_keys, idx, model, store_name, store_link, semaphore, ws, desc_col):
    """مهمة معالجة منتج واحد (تعمل بالتزامن مع مهام أخرى)"""
    num_keys = len(active_keys)
    current_key_index = idx % num_keys
    current_key = active_keys[current_key_index]
    provider = get_api_provider(current_key)

    data = await fetch_notes_async(session, pname, current_key, model, store_name, provider, semaphore)
    
    if data and isinstance(data, dict):
        html = build_html_salla(pname, data, store_name, store_link)
        ws.cell(row=row_i + 3, column=desc_col).value = html
        return {"name": pname, "ok": True}
    return {"name": pname, "ok": False}

async def run_batch_async(tasks, active_keys, model, store_name, store_link, concurrency_limit, progress_bar, status_text, ws, desc_col):
    """إدارة المهام المتزامنة وتحديث الواجهة"""
    semaphore = asyncio.Semaphore(concurrency_limit)
    total = len(tasks)
    results = []
    completed = 0

    async with aiohttp.ClientSession() as session:
        coroutines = []
        for idx, (row_i, pname) in enumerate(tasks):
            coro = process_product(session, row_i, pname, active_keys, idx, model, store_name, store_link, semaphore, ws, desc_col)
            coroutines.append(coro)

        # تنفيذ المهام وتحديث شريط التقدم فور اكتمال أي منتج
        for future in asyncio.as_completed(coroutines):
            res = await future
            results.append(res)
            completed += 1
            progress_bar.progress(completed / total)
            status_text.markdown(f'<div class="product-item">⚡ <strong>تم إنجاز ({completed}/{total}) منتج بنجاح..</strong><br>آخر منتج تمت معالجته: {res["name"]}</div>', unsafe_allow_html=True)

    return results

def process_file_manager(uploaded, active_keys, model, store_name, store_link, process_all, start_skip, batch_size, concurrency_limit, bar, status):
    """المدير الرئيسي لعمليات الملف والحفظ الطارئ"""
    raw = uploaded.getvalue()
    wb = openpyxl.load_workbook(io.BytesIO(raw))
    ws = wb.active
    df = pd.read_excel(io.BytesIO(raw), header=1)

    cols = list(df.columns)
    desc_col = cols.index("الوصف") + 1
    
    tasks = []
    for i, row in df.iterrows():
        should_process = process_all or is_empty(row["الوصف"])
        n = str(row["أسم المنتج"]).strip()
        if should_process and n and n != "nan":
            tasks.append((i, n))

    tasks = tasks[start_skip:]
    tasks = tasks[:batch_size]

    if len(tasks) == 0:
        return None, [], 0

    # بدء تشغيل الحلقة اللامتزامنة (Asyncio Event Loop)
    results = []
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            run_batch_async(tasks, active_keys, model, store_name, store_link, concurrency_limit, bar, status, ws, desc_col)
        )
    except Exception as e:
        st.warning(f"⚠️ توقف طارئ بسبب الضغط، ولكن تم حفظ تقدمك بأمان!")
    finally:
        loop.close()
        
        # حفظ الملف في كل الأحوال (نجاح أو فشل)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        
        success_count = sum(1 for r in results if r["ok"])
        return buf, results, success_count

# ══════════════════════════════════════════════════════════════
#  الواجهة الجانبية (Sidebar)
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙️ الإعدادات المتقدمة (Enterprise)")
    batch_size = st.number_input("الحد الأقصى للمنتجات في الدفعة:", min_value=1, max_value=3000, value=500, help="بفضل السرعة الجديدة، يمكنك رفع الدفعة حتى 500 أو 1000.")
    concurrency_limit = st.slider("عدد الطلبات المتزامنة (السرعة):", min_value=1, max_value=15, value=5, help="كلما زاد الرقم، زادت السرعة، لكن قد يسبب حظر مؤقت من جوجل.")
    start_skip = st.number_input("تخطي أول (X) منتج:", min_value=0, value=0)

    st.markdown("---")
    st.markdown("### 🔑 مفاتيح API")
    key1 = st.text_input("المفتاح الأول", type="password")
    key2 = st.text_input("المفتاح الثاني", type="password")
    key3 = st.text_input("المفتاح الثالث", type="password")
    active_keys = [k.strip() for k in [key1, key2, key3] if k.strip()]
    model_name = st.selectbox("النموذج", list(MODELS.keys()))

    st.markdown("---")
    st.markdown("### 🏪 بيانات المتجر")
    store_name = st.text_input("اسم المتجر", value="لي غابريال")
    store_link = st.text_input("رابط المتجر", value="https://legabreil.com/ar")

    st.markdown("---")
    process_mode = st.radio("خيارات المعالجة:", ["المنتجات الفارغة فقط", "الكل (إعادة كتابة)"], index=0)
    process_all = (process_mode == "الكل (إعادة كتابة)")

# ══════════════════════════════════════════════════════════════
#  الواجهة الرئيسية
# ══════════════════════════════════════════════════════════════

st.title("⚡ مولّد أوصاف العطور (النسخة الصاروخية)")
st.info("🚀 تم ترقية التطبيق ليعمل بنظام (Asynchronous) المتزامن. أصبح التطبيق يعالج المنتجات بأضعاف السرعة السابقة مع ضمان الحفظ التلقائي.")

uploaded = st.file_uploader("ارفع ملف المنتجات (Excel)", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded, header=1)
    
    total_products = len(df)
    empty_desc = df["الوصف"].apply(is_empty).sum()
    target_count = total_products if process_all else empty_desc
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 إجمالي المنتجات", total_products)
    c2.metric("📝 المنتجات المستهدفة إجمالاً", target_count)
    c3.metric("🎯 سيعالج في هذه الدفعة", min(target_count - start_skip, batch_size))

    if st.button("🚀 ابدأ المعالجة السريعة الآن", type="primary"):
        if not active_keys:
            st.error("❌ الرجاء إدخال مفتاح API واحد على الأقل.")
        elif target_count == 0:
            st.warning("⚠️ لا توجد منتجات للمعالجة.")
        else:
            bar = st.progress(0)
            status = st.empty()
            
            buf, results, success = process_file_manager(
                uploaded, active_keys, MODELS[model_name], 
                store_name, store_link, process_all, start_skip, batch_size, concurrency_limit, bar, status
            )
            
            bar.progress(100)
            status.empty()
            
            if len(results) > 0:
                st.success(f"✅ اكتملت الدفعة بنجاح! تمت صياغة {success} وصف جديد.")
                st.download_button(
                    "📥 تحميل الملف المحدّث وحفظ التقدم",
                    data=buf,
                    file_name="products_batch_fast_async.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                if success < len(results):
                    st.warning(f"ملاحظة: كان هناك {len(results)-success} منتج لم يتم التعرف عليها من قبل الذكاء الاصطناعي، يمكنك إعادة رفع الملف لاحقاً لإعادة محاولتها.")
            else:
                st.error("❌ لم يتم توليد أي بيانات. تأكد من صحة مفاتيح الـ API.")
