import streamlit as st
import pandas as pd
import requests
import json
import time
import io
import re
import openpyxl

# ══════════════════════════════════════════════════════════════
#  مولّد أوصاف عطور احترافي (نسخة SEO المتقدمة)
#  متوافق مع سلة + Google Merchant + خيار تحديث الكل
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
    background:#fafafa;border-right:4px solid #d4af37;
    border-radius:8px;padding:10px 16px;margin:5px 0;font-size:14px
}
.done-box{
    background:linear-gradient(145deg,#f0fdf4,#dcfce7);
    border:2px solid #22c55e;border-radius:16px;padding:24px;text-align:center;
    box-shadow:0 4px 12px rgba(34,197,94,.15)
}
.fail-box{
    background:#fef2f2;border:2px solid #ef4444;border-radius:16px;padding:24px;text-align:center
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    "Google Gemini 2.0 Flash (سريع)": "google/gemini-2.0-flash-001",
    "Google Gemini 2.0 Flash (مجاني)": "google/gemini-2.0-flash-exp:free",
    "Google Gemini Flash 1.5": "google/gemini-flash-1.5",
    "Llama 3.1 8B (مجاني)": "meta-llama/llama-3.1-8b-instruct:free",
    "GPT-4o Mini": "openai/gpt-4o-mini",
    "Claude Sonnet 4": "anthropic/claude-sonnet-4",
}

# ─── Helper Functions ───
def is_empty(val) -> bool:
    if pd.isna(val):
        return True
    s = str(val).strip()
    return s in ("", "nan", "<p></p>", "<p><br></p>", "None", "<p> </p>")

def fetch_notes(name: str, api_key: str, model: str, store_name: str) -> dict | None:
    """جلب معلومات مفصلة وطويلة جداً لأغراض SEO"""

    system_msg = """أنت خبير محتوى وتسويق إلكتروني (SEO Specialist) متخصص في العطور.
مهمتك: كتابة محتوى تسويقي ثري، طويل، وجذاب لمحركات البحث (Google Merchant).
المتطلبات:
1. المعلومات يجب أن تكون دقيقة 100% بناءً على Fragrantica.
2. اللغة عربية فصحى جذابة ومؤثرة.
3. تجنب التكرار الممل، وركز على "تجربة المستخدم" و"المشاعر".
4. أرجع النتيجة بصيغة JSON فقط."""

    user_msg = f"""اكتب وصفاً احترافياً شاملاً للمنتج التالي:
اسم المنتج: "{name}"
اسم المتجر الذي سيبيع المنتج: "{store_name}"

أرجع JSON بهذا الهيكل بالضبط (تأكد أن النصوص طويلة وغنية):
{{
  "perfume_en": "الاسم الإنجليزي الكامل للعطر",
  "brand_ar": "اسم الماركة بالعربي",
  "year": "سنة الإصدار",
  "perfumer": "اسم العطار",
  "family_ar": "العائلة العطرية بالعربي",
  "gender": "جنس العطر",
  "concentration_ar": "التركيز بالعربي",
  "intro_story": "مقدمة إبداعية طويلة (لا تقل عن 100 كلمة) تحكي قصة العطر، لمن صُمم، وما الشعور الذي يعطيه. استخدم كلمات مفتاحية قوية.",
  "ingredients_desc": "شرح نصي مفصل للمكونات (ليس مجرد قائمة). اشرح كيف تتناغم المقدمة مع القلب والقاعدة (لا يقل عن 80 كلمة).",
  "top_notes": "المكونات العليا",
  "heart_notes": "المكونات الوسطى",
  "base_notes": "المكونات الأساسية",
  "usage_occasion": "شرح مفصل: متى يُستخدم هذا العطر؟ (صباحي/مسائي، فصول السنة، مناسبات رسمية/يومية) ولماذا؟",
  "user_persona": "وصف للشخصية التي يناسبها هذا العطر (مثلاً: الرجل الجريء، المرأة العصرية..).",
  "seo_keywords": "5 كلمات مفتاحية قوية مفصولة بفواصل"
}}
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://perfume-desc-generator.streamlit.app",
        "X-Title": "Perfume Description Generator",
    }

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3, # زدت الحرارة قليلاً للإبداع في النصوص الطويلة
        "max_tokens": 2500,
    }

    try:
        r = requests.post(API_URL, headers=headers, json=body, timeout=120)
        if r.status_code != 200:
            st.warning(f"⚠️ API Error {r.status_code}")
            return None
        text = r.json()["choices"][0]["message"]["content"].strip()
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?\s*```$", "", text)
        return json.loads(text)
    except Exception as e:
        return None

def build_html_salla(name: str, d: dict, store_name: str, store_link: str, store_bio: str) -> str:
    """بناء HTML متوافق مع سلة بتنسيق احترافي وعناوين كبيرة"""

    # استخراج البيانات
    perfume_en = d.get("perfume_en", "")
    intro_story = d.get("intro_story", "")
    ingredients_desc = d.get("ingredients_desc", "")
    usage = d.get("usage_occasion", "")
    persona = d.get("user_persona", "")
    
    # تفاصيل تقنية
    family = d.get("family_ar", "")
    conc = d.get("concentration_ar", "")
    year = d.get("year", "")
    perfumer = d.get("perfumer", "")
    
    # نوتات
    top = d.get("top_notes", "")
    heart = d.get("heart_notes", "")
    base = d.get("base_notes", "")

    # روابط المتجر
    if store_name and store_link:
        store_ref = f'<a href="{store_link}" style="color: #d4af37; text-decoration: none; font-weight: bold;">{store_name}</a>'
    elif store_name:
        store_ref = f'<span style="color: #d4af37; font-weight: bold;">{store_name}</span>'
    else:
        store_ref = "المتجر"

    # معالجة الحجم والتستر من الاسم
    m = re.search(r"(\d+)\s*مل", name)
    size = m.group(0) if m else "متوفر في خيارات المنتج"
    is_tester = "تستر" in name or "tester" in name.lower()

    # ─── بداية بناء كود HTML ───
    # ملاحظة: نستخدم Inline CSS لضمان التوافق مع محرر سلة الذي قد يحذف كلاسات CSS الخارجية
    
    html = f"""
    <div style="font-family: 'Tajawal', sans-serif; text-align: right; direction: rtl; line-height: 1.8; color: #333;">
        
        <p style="font-size: 16px; margin-bottom: 20px;">
            {intro_story} يقدمه لك {store_ref} ليكون إضافة فاخرة لمجموعتك الشخصية.
        </p>

        <h2 style="font-size: 24px; color: #b8960c; background-color: #fcfbf5; padding: 10px 15px; border-right: 5px solid #d4af37; border-radius: 4px; margin-top: 30px; margin-bottom: 15px;">
            مواصفات العطر
        </h2>
        <ul style="list-style-type: none; padding-right: 10px; font-size: 15px;">
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;">
                <strong>🏷️ اسم الماركة:</strong> {d.get('brand_ar', '')}
            </li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;">
                <strong>📦 الاسم بالإنجليزية:</strong> {perfume_en}
            </li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;">
                <strong>💧 التركيز:</strong> {conc}
            </li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;">
                <strong>📏 الحجم:</strong> {size}
            </li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;">
                <strong>👃 العائلة العطرية:</strong> {family}
            </li>
             <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;">
                <strong>📅 سنة الإصدار:</strong> {year}
            </li>
        </ul>

        <h2 style="font-size: 24px; color: #b8960c; background-color: #fcfbf5; padding: 10px 15px; border-right: 5px solid #d4af37; border-radius: 4px; margin-top: 30px; margin-bottom: 15px;">
            الهرم العطري والمكونات
        </h2>
        <p style="margin-bottom: 15px;">{ingredients_desc}</p>
        
        <div style="background: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
            <p style="margin-bottom: 8px;"><strong>🍋 النوتات العليا (الافتتاحية):</strong><br> {top}</p>
            <p style="margin-bottom: 8px;"><strong>🌸 النوتات الوسطى (القلب):</strong><br> {heart}</p>
            <p style="margin-bottom: 0;"><strong>🪵 النوتات الأساسية (القاعدة):</strong><br> {base}</p>
        </div>

        <h2 style="font-size: 24px; color: #b8960c; background-color: #fcfbf5; padding: 10px 15px; border-right: 5px solid #d4af37; border-radius: 4px; margin-top: 30px; margin-bottom: 15px;">
            متى تستخدم هذا العطر؟
        </h2>
        <p><strong>أوقات الاستخدام:</strong> {usage}</p>
        <p><strong>هل يناسبني؟</strong> {persona}</p>

    """

    # قسم التستر (يظهر فقط إذا كان تستر)
    if is_tester:
        html += """
        <div style="margin-top: 20px; padding: 15px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 6px; color: #856404;">
            <strong>⚠️ ملاحظة حول عطور التستر:</strong><br>
            هذا المنتج هو "تستر" (Tester)، وهو النسخة الأصلية 100% التي توفرها الماركة للتجربة. يأتي عادةً بكرتون أبيض أو بني، وقد يأتي بدون غطاء أحياناً. هو خيار اقتصادي ممتاز للاستخدام الشخصي (نفس الرائحة والثبات) وأقل ملاءمة كهدية.
        </div>
        """

    # نبذة عن المتجر (الخاتمة)
    if store_name and store_bio:
        html += f"""
        <hr style="border: 0; border-top: 1px solid #eee; margin: 40px 0;">
        <div style="text-align: center; background: #fdfdfd; padding: 20px; border-radius: 10px;">
            <h3 style="color: #d4af37; margin-bottom: 10px;">لماذا تتسوق من {store_name}؟</h3>
            <p>{store_bio}</p>
            <p style="margin-top: 10px;">
                <a href="{store_link}" style="background-color: #d4af37; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">تصفح المزيد من العطور</a>
            </p>
        </div>
        """

    html += "</div>"
    
    # تنظيف
    html = html.replace("\n", "").replace("\r", "")
    return html

def process_file(uploaded, api_key, model, store_name, store_link, store_bio, process_all, bar, status):
    raw = uploaded.getvalue()
    wb = openpyxl.load_workbook(io.BytesIO(raw))
    ws = wb.active
    df = pd.read_excel(io.BytesIO(raw), header=1)

    cols = list(df.columns)
    if "الوصف" not in cols or "أسم المنتج" not in cols:
        st.error("❌ تأكد من وجود أعمدة: 'أسم المنتج' و 'الوصف'")
        return None, [], 0

    desc_col = cols.index("الوصف") + 1
    
    tasks = []
    for i, row in df.iterrows():
        # المنطق الجديد: إذا "تحديث الكل" مفعّل نأخذ الكل، وإلا نأخذ الفارغ فقط
        should_process = process_all or is_empty(row["الوصف"])
        
        n = str(row["أسم المنتج"]).strip()
        if should_process and n and n != "nan":
            tasks.append((i, n))

    total = len(tasks)
    if total == 0:
        return None, [], 0

    results = []
    success = 0

    for idx, (row_i, pname) in enumerate(tasks):
        pct = (idx + 1) / total
        bar.progress(pct)
        status.markdown(
            f'<div class="product-item">⏳ <strong>جاري الكتابة ({idx+1}/{total})</strong><br>{pname}</div>',
            unsafe_allow_html=True,
        )

        data = fetch_notes(pname, api_key, model, store_name)

        if data:
            html = build_html_salla(pname, data, store_name, store_link, store_bio)
            excel_row = row_i + 3
            # مسح المحتوى القديم وكتابة الجديد
            ws.cell(row=excel_row, column=desc_col).value = html
            results.append({"name": pname, "ok": True})
            success += 1
        else:
            results.append({"name": pname, "ok": False})
        
        time.sleep(1.5)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf, results, success

def test_api(api_key, model):
    # دالة اختبار بسيطة (نفس القديمة)
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        body = {"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
        r = requests.post(API_URL, headers=headers, json=body, timeout=10)
        return r.status_code == 200, "اتصال ناجح" if r.status_code == 200 else f"Error {r.status_code}"
    except Exception as e:
        return False, str(e)

# ══════════════════════════════════════════════════════════════
#  واجهة التطبيق (UI)
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙️ الإعدادات")
    api_key = st.text_input("مفتاح API", type="password")
    model_name = st.selectbox("النموذج", list(MODELS.keys()))
    
    if st.button("اختبار الاتصال"):
        ok, msg = test_api(api_key, MODELS[model_name])
        if ok: st.success(msg)
        else: st.error(msg)

    st.markdown("---")
    st.markdown("### 🏪 بيانات المتجر")
    store_name = st.text_input("اسم المتجر", value="اسم متجرك")
    store_link = st.text_input("رابط المتجر", placeholder="https://...")
    store_bio = st.text_area(
        "نبذة عن المتجر (ستظهر أسفل كل وصف)",
        value="نحن متجر سعودي متخصص في العطور الأصلية والنيش، نسعى لتقديم تجربة عطرية فاخرة بضمان ذهبي وأسعار منافسة.",
        height=100
    )

    st.markdown("---")
    st.markdown("### 🎯 خيارات المعالجة")
    process_mode = st.radio(
        "أي المنتجات تريد معالجتها؟",
        ["المنتجات التي ليس لها وصف فقط (تكملة)", "تحديث جميع المنتجات (إعادة كتابة الكل)"],
        index=0
    )
    process_all = (process_mode == "تحديث جميع المنتجات (إعادة كتابة الكل)")

st.title("✨ مولّد أوصاف العطور الاحترافي (SEO)")
st.info("💡 هذا الإصدار يدعم كتابة مقالات طويلة، توافق تام مع سلة، وإمكانية تحديث جميع المنتجات.")

uploaded = st.file_uploader("ارفع ملف المنتجات (Excel)", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded, header=1)
    
    # إحصائيات سريعة
    total_products = len(df)
    empty_desc = df["الوصف"].apply(is_empty).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي المنتجات", total_products)
    c2.metric("بدون وصف", empty_desc)
    
    target_count = total_products if process_all else empty_desc
    c3.metric("العدد المستهدف للمعالجة", target_count)

    if st.button("🚀 ابدأ المعالجة الآن", type="primary"):
        if not api_key:
            st.error("الرجاء إدخال مفتاح API")
        elif target_count == 0:
            st.warning("لا توجد منتجات للمعالجة بناءً على اختيارك.")
        else:
            bar = st.progress(0)
            status = st.empty()
            
            buf, results, success = process_file(
                uploaded, api_key, MODELS[model_name], 
                store_name, store_link, store_bio, process_all, bar, status
            )
            
            bar.progress(100)
            status.success(f"تمت العملية! نجح: {success} | فشل: {len(results)-success}")
            
            st.download_button(
                "📥 تحميل الملف الجاهز",
                data=buf,
                file_name="products_updated_seo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
