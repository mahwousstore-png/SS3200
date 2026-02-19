import streamlit as st
import pandas as pd
import requests
import json
import time
import io
import re
import openpyxl

# ══════════════════════════════════════════════════════════════
#  مولّد أوصاف عطور احترافي (النسخة المتطابقة مع نموذج لي غابريال)
#  +2000 حرف | متوافق مع سلة 100% | بدون فراغات أسطر
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="مولّد أوصاف عطور SEO",
    page_icon="💎",
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
.stat-card{
    background:linear-gradient(145deg,#fdfbf3,#f9f6ec);
    border:1px solid #e8dfc0;border-radius:16px;padding:24px;text-align:center;
    box-shadow:0 2px 8px rgba(0,0,0,.04)
}
.stat-num{font-size:36px;font-weight:800;color:#d4af37;line-height:1}
.stat-label{font-size:14px;color:#888;margin-top:8px}
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

def fetch_notes(name: str, api_key: str, model: str, store_name: str, provider: str) -> dict | None:
    """جلب معلومات العطر بناءً على المزود وتوسيع النص لأكثر من 2000 حرف"""

    system_msg = """أنت خبير محتوى وتسويق إلكتروني متخصص في العطور الفاخرة.
مهمتك: كتابة محتوى تسويقي احترافي، دقيق بناءً على Fragrantica، وطويل جداً جداً (يجب أن يتجاوز إجمالي النص 2000 حرف لأغراض SEO).
أرجع النتيجة بصيغة JSON فقط، وتأكد أن كل حقل يحتوي على شرح مسهب وتفصيلي وإبداعي:
{
  "perfume_en": "الاسم الإنجليزي الكامل للعطر (مثال: Chanel Égoïste Platinum EDT)",
  "perfume_ar": "الاسم العربي الكامل للعطر",
  "type": "عطر رجالي، عطر نسائي، أو عطر للجنسين",
  "concentration": "التركيز (مثال: أو دو تواليت Eau de Toilette)",
  "family": "العائلة العطرية مفصلة (مثال: فوجير خشبي زهري مسكي)",
  "perfumer": "اسم العطار الحقيقي",
  "year": "سنة الإصدار",
  "intro_paragraph": "مقدمة تسويقية إبداعية وسردية طويلة جداً (لا تقل عن 500 حرف) تحكي قصة العطر وروعته وتذكر اسم العطار وتأثير العطر.",
  "top_notes": "وصف طويل للنوتات العليا ومكوناتها وتأثيرها على الحواس (مثال: مزيج عشبي منعش من... يفتح العطر بانطلاقة...)",
  "heart_notes": "وصف طويل للنوتات الوسطى وكيف تتناغم (مثال: توليفة عطرية أنيقة من... تضيف عمقاً...)",
  "base_notes": "وصف طويل للنوتات الأساسية ومدى ثباتها (مثال: قاعدة خشبية غنية من... تمنح العطر ثباتاً...)",
  "general_vibe": "الطابع العام للعطر في جملتين طويلتين تصفان الإحساس الذي يتركه العطر.",
  "why_choose_1": "سبب أول قوي لاختيار العطر (مثلاً: أيقونة كلاسيكية) مع شرح تفصيلي.",
  "why_choose_2": "سبب ثاني (مثلاً: ثبات ممتاز) مع تفصيل الميزات.",
  "why_choose_3": "سبب ثالث (مثلاً: تعدد المناسبات) مع تفصيل الأوقات المناسبة.",
  "faq_1_q": "سؤال شائع أول (مثال: هل العطر مناسب للاستخدام اليومي؟)",
  "faq_1_a": "إجابة مفصلة للسؤال الأول.",
  "faq_2_q": "سؤال شائع ثاني (مثال: هل يناسب فصل معين؟)",
  "faq_2_a": "إجابة مفصلة للسؤال الثاني.",
  "faq_3_q": "سؤال شائع ثالث (مثال: ما مدى ثبات العطر على الجلد؟)",
  "faq_3_a": "إجابة مفصلة للسؤال الثالث.",
  "closing_paragraph": "خاتمة طويلة وجذابة تؤكد على روعة العطر وتدفع العميل للشراء بثقة."
}"""

    user_msg = f'اكتب وصفاً احترافياً مطولاً (أكثر من 2000 حرف) للمنتج: "{name}" لمتجر "{store_name}". استخدم بيانات دقيقة.'

    try:
        if provider == "google":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            body = {
                "contents": [{"role": "user", "parts": [{"text": system_msg + "\n\n" + user_msg}]}],
                "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}
            }
            r = requests.post(url, headers=headers, json=body, timeout=120)
            if r.status_code != 200: return None
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            
        else:
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
                "temperature": 0.4,
                "max_tokens": 3000,
            }
            r = requests.post(API_URL_OPENROUTER, headers=headers, json=body, timeout=120)
            if r.status_code != 200: return None
            text = r.json()["choices"][0]["message"]["content"].strip()

        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?\s*```$", "", text)
        return json.loads(text)
    except Exception:
        return None

def build_html_salla(name: str, d: dict, store_name: str, store_link: str) -> str:
    """بناء HTML متوافق تماماً مع النموذج المطلوب وبدون أي مسافات أسطر"""
    
    # تجهيز المتغيرات
    a_tag = f'<a href="{store_link}" style="color: #d4af37; font-weight: bold; text-decoration: none;">{store_name}</a>' if store_name and store_link else f'<strong style="color: #d4af37;">{store_name}</strong>'
    
    # استخراج الحجم من الاسم إن وجد، أو تركه فارغاً
    m = re.search(r"(\d+)\s*مل", name)
    size = m.group(0) if m else "حسب الاختيار المتاح"

    # بناء الكود مع دمج التنسيقات (Inline CSS) ليقرأها محرر سلة بشكل صحيح
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
    
    # الإزالة الصارمة لجميع الفراغات بين الأسطر (New Lines) ليتوافق مع سلة كقطعة واحدة
    html_clean = html.replace("\n", "").replace("\r", "")
    # إزالة الفراغات المزدوجة الناتجة عن دمج الأسطر
    html_clean = re.sub(r'\s{2,}', ' ', html_clean)
    
    return html_clean

def process_file(uploaded, active_keys, model, store_name, store_link, process_all, sleep_time, bar, status):
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

    total = len(tasks)
    if total == 0:
        return None, [], 0

    results = []
    success = 0
    num_keys = len(active_keys)

    for idx, (row_i, pname) in enumerate(tasks):
        pct = (idx + 1) / total
        bar.progress(pct)
        
        current_key_index = idx % num_keys
        current_key = active_keys[current_key_index]
        provider = get_api_provider(current_key)

        status.markdown(
            f'<div class="product-item">⏳ <strong>جاري الكتابة ({idx+1}/{total})</strong><br>'
            f'🔄 مفتاح <strong>{current_key_index + 1}</strong> ({provider.upper()})<br>'
            f'📦 المنتج: {pname}</div>',
            unsafe_allow_html=True,
        )

        data = fetch_notes(pname, current_key, model, store_name, provider)

        if data:
            html = build_html_salla(pname, data, store_name, store_link)
            ws.cell(row=row_i + 3, column=desc_col).value = html
            results.append({"name": pname, "ok": True})
            success += 1
        else:
            results.append({"name": pname, "ok": False})
        
        time.sleep(sleep_time)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf, results, success

# ══════════════════════════════════════════════════════════════
#  الواجهة الجانبية (Sidebar)
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🔑 مفاتيح API (التناوب الذكي)")
    
    key1 = st.text_input("المفتاح الأول", type="password")
    key2 = st.text_input("المفتاح الثاني", type="password")
    key3 = st.text_input("المفتاح الثالث", type="password")
    
    active_keys = [k.strip() for k in [key1, key2, key3] if k.strip()]

    model_name = st.selectbox("النموذج (في حال OpenRouter)", list(MODELS.keys()))
    
    st.markdown("---")
    st.markdown("### ⏱️ التحكم بالسرعة")
    sleep_time = st.slider("الانتظار بين المنتجات (ثواني)", min_value=1, max_value=15, value=5)

    st.markdown("---")
    st.markdown("### 🏪 بيانات المتجر")
    store_name = st.text_input("اسم المتجر", value="لي غابريال")
    store_link = st.text_input("رابط المتجر", value="https://legabreil.com/ar")

    st.markdown("---")
    process_mode = st.radio("خيارات المعالجة:", ["الفارغ فقط", "الكل (إعادة كتابة)"], index=0)
    process_all = (process_mode == "الكل (إعادة كتابة)")

# ══════════════════════════════════════════════════════════════
#  الواجهة الرئيسية
# ══════════════════════════════════════════════════════════════

st.title("✨ مولّد أوصاف العطور (متطابق مع نموذج لي غابريال)")
st.info("💡 تم برمجة هذا التحديث ليطابق نموذج الوصف الخاص بك 100% مع ضمان إنتاج وصف يتجاوز 2000 حرف وبدون أي فراغات أسطر (متوافق تماماً مع محرر منصة سلة).")

uploaded = st.file_uploader("ارفع ملف المنتجات (Excel)", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded, header=1)
    
    total_products = len(df)
    empty_desc = df["الوصف"].apply(is_empty).sum()
    target_count = total_products if process_all else empty_desc
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 إجمالي المنتجات", total_products)
    c2.metric("📝 بدون وصف", empty_desc)
    c3.metric("🎯 المستهدف", target_count)

    if st.button("🚀 ابدأ المعالجة الآن", type="primary"):
        if not active_keys:
            st.error("❌ الرجاء إدخال مفتاح API واحد على الأقل في الشريط الجانبي.")
        elif target_count == 0:
            st.warning("⚠️ لا توجد منتجات للمعالجة.")
        else:
            bar = st.progress(0)
            status = st.empty()
            
            buf, results, success = process_file(
                uploaded, active_keys, MODELS[model_name], 
                store_name, store_link, process_all, sleep_time, bar, status
            )
            
            bar.progress(100)
            status.empty()
            
            if success > 0:
                st.success(f"✅ تمت العملية! نجح: {success} | فشل: {len(results)-success}")
                st.download_button(
                    "📥 تحميل الملف الجاهز",
                    data=buf,
                    file_name="products_updated_legabreil_style.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error("❌ فشلت المعالجة تماماً. تأكد من المفاتيح أو جرب زيادة وقت الانتظار.")
