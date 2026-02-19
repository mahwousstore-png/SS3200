import streamlit as st
import pandas as pd
import requests
import json
import time
import io
import re
import openpyxl

# ══════════════════════════════════════════════════════════════
#  مولّد أوصاف عطور احترافي (نسخة SEO المتقدمة - ثنائي المحركات)
#  متوافق مع سلة + Google Merchant + دعم مباشر لمفاتيح Google و OpenRouter
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
    """تحديد مزود الخدمة تلقائياً بناءً على بداية المفتاح"""
    if api_key.startswith("AIza"):
        return "google"
    return "openrouter"

def fetch_notes(name: str, api_key: str, model: str, store_name: str, provider: str) -> dict | None:
    """جلب معلومات العطر بناءً على المزود (Google أو OpenRouter)"""

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

أرجع JSON بهذا الهيكل بالضبط:
{{
  "perfume_en": "الاسم الإنجليزي الكامل للعطر",
  "brand_ar": "اسم الماركة بالعربي",
  "year": "سنة الإصدار",
  "perfumer": "اسم العطار",
  "family_ar": "العائلة العطرية بالعربي",
  "gender": "جنس العطر",
  "concentration_ar": "التركيز بالعربي",
  "intro_story": "مقدمة إبداعية طويلة (لا تقل عن 100 كلمة) تحكي قصة العطر.",
  "ingredients_desc": "شرح نصي مفصل للمكونات وكيف تتناغم (لا يقل عن 80 كلمة).",
  "top_notes": "المكونات العليا",
  "heart_notes": "المكونات الوسطى",
  "base_notes": "المكونات الأساسية",
  "usage_occasion": "متى يُستخدم هذا العطر ولماذا؟",
  "user_persona": "وصف للشخصية التي يناسبها هذا العطر.",
  "seo_keywords": "5 كلمات مفتاحية قوية مفصولة بفواصل"
}}
"""

    if provider == "google":
        # الاتصال المباشر بسيرفرات جوجل (للمفاتيح التي تبدأ بـ AIza)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [
                {"role": "user", "parts": [{"text": system_msg + "\n\n" + user_msg}]}
            ],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json"
            }
        }
        
        try:
            r = requests.post(url, headers=headers, json=body, timeout=120)
            if r.status_code != 200:
                st.warning(f"⚠️ خطأ في API جوجل ({r.status_code}): نفد الرصيد أو استهلاك سريع جداً.")
                return None
            
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?\s*```$", "", text)
            return json.loads(text)
        except Exception as e:
            return None

    else:
        # الاتصال بسيرفرات OpenRouter
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
            "temperature": 0.3,
            "max_tokens": 2500,
        }
        
        try:
            r = requests.post(API_URL_OPENROUTER, headers=headers, json=body, timeout=120)
            if r.status_code != 200:
                st.warning(f"⚠️ خطأ في OpenRouter ({r.status_code})")
                return None
            
            text = r.json()["choices"][0]["message"]["content"].strip()
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?\s*```$", "", text)
            return json.loads(text)
        except Exception as e:
            return None

def build_html_salla(name: str, d: dict, store_name: str, store_link: str, store_bio: str) -> str:
    """بناء HTML متوافق مع سلة"""
    perfume_en = d.get("perfume_en", "")
    intro_story = d.get("intro_story", "")
    ingredients_desc = d.get("ingredients_desc", "")
    usage = d.get("usage_occasion", "")
    persona = d.get("user_persona", "")
    family = d.get("family_ar", "")
    conc = d.get("concentration_ar", "")
    year = d.get("year", "")
    top = d.get("top_notes", "")
    heart = d.get("heart_notes", "")
    base = d.get("base_notes", "")

    store_ref = f'<a href="{store_link}" style="color: #d4af37; text-decoration: none; font-weight: bold;">{store_name}</a>' if (store_name and store_link) else f'<span style="color: #d4af37; font-weight: bold;">{store_name}</span>' if store_name else "المتجر"

    m = re.search(r"(\d+)\s*مل", name)
    size = m.group(0) if m else "متوفر بخيارات متعددة"
    is_tester = "تستر" in name or "tester" in name.lower()

    html = f"""
    <div style="font-family: 'Tajawal', sans-serif; text-align: right; direction: rtl; line-height: 1.8; color: #333;">
        <p style="font-size: 16px; margin-bottom: 20px;">
            {intro_story} يقدمه لك {store_ref} ليكون إضافة فاخرة لمجموعتك الشخصية.
        </p>
        <h2 style="font-size: 24px; color: #b8960c; background-color: #fcfbf5; padding: 10px 15px; border-right: 5px solid #d4af37; border-radius: 4px; margin-top: 30px; margin-bottom: 15px;">
            مواصفات العطر
        </h2>
        <ul style="list-style-type: none; padding-right: 10px; font-size: 15px;">
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;"><strong>🏷️ اسم الماركة:</strong> {d.get('brand_ar', '')}</li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;"><strong>📦 الاسم بالإنجليزية:</strong> {perfume_en}</li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;"><strong>💧 التركيز:</strong> {conc}</li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;"><strong>📏 الحجم:</strong> {size}</li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;"><strong>👃 العائلة العطرية:</strong> {family}</li>
            <li style="margin-bottom: 8px; border-bottom: 1px dashed #eee; padding-bottom: 5px;"><strong>📅 سنة الإصدار:</strong> {year}</li>
        </ul>
        <h2 style="font-size: 24px; color: #b8960c; background-color: #fcfbf5; padding: 10px 15px; border-right: 5px solid #d4af37; border-radius: 4px; margin-top: 30px; margin-bottom: 15px;">
            الهرم العطري والمكونات
        </h2>
        <p style="margin-bottom: 15px;">{ingredients_desc}</p>
        <div style="background: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
            <p style="margin-bottom: 8px;"><strong>🍋 الافتتاحية:</strong> {top}</p>
            <p style="margin-bottom: 8px;"><strong>🌸 القلب:</strong> {heart}</p>
            <p style="margin-bottom: 0;"><strong>🪵 القاعدة:</strong> {base}</p>
        </div>
        <h2 style="font-size: 24px; color: #b8960c; background-color: #fcfbf5; padding: 10px 15px; border-right: 5px solid #d4af37; border-radius: 4px; margin-top: 30px; margin-bottom: 15px;">
            متى تستخدم هذا العطر؟
        </h2>
        <p><strong>أوقات الاستخدام:</strong> {usage}</p>
        <p><strong>هل يناسبني؟</strong> {persona}</p>
    """

    if is_tester:
        html += """
        <div style="margin-top: 20px; padding: 15px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 6px; color: #856404;">
            <strong>⚠️ ملاحظة حول عطور التستر:</strong><br>
            هذا المنتج هو "تستر" (Tester)، وهو النسخة الأصلية 100% التي توفرها الماركة للتجربة. خيار اقتصادي ممتاز للاستخدام الشخصي بنفس جودة وثبات العطر المغلف.
        </div>
        """

    if store_name and store_bio:
        html += f"""
        <hr style="border: 0; border-top: 1px solid #eee; margin: 40px 0;">
        <div style="text-align: center; background: #fdfdfd; padding: 20px; border-radius: 10px;">
            <h3 style="color: #d4af37; margin-bottom: 10px;">لماذا تتسوق من {store_name}؟</h3>
            <p>{store_bio}</p>
            <p style="margin-top: 10px;">
                <a href="{store_link}" style="background-color: #d4af37; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">تصفح المزيد من منتجاتنا</a>
            </p>
        </div>
        """

    html += "</div>"
    return html.replace("\n", "").replace("\r", "")

def process_file(uploaded, api_key, model, store_name, store_link, store_bio, process_all, sleep_time, bar, status):
    raw = uploaded.getvalue()
    wb = openpyxl.load_workbook(io.BytesIO(raw))
    ws = wb.active
    df = pd.read_excel(io.BytesIO(raw), header=1)

    provider = get_api_provider(api_key)
    
    cols = list(df.columns)
    if "الوصف" not in cols or "أسم المنتج" not in cols:
        st.error("❌ تأكد من وجود أعمدة: 'أسم المنتج' و 'الوصف'")
        return None, [], 0

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

    for idx, (row_i, pname) in enumerate(tasks):
        pct = (idx + 1) / total
        bar.progress(pct)
        status.markdown(
            f'<div class="product-item">⏳ <strong>جاري الكتابة ({idx+1}/{total})</strong><br>المزود: <strong>{provider.upper()}</strong> | المنتج: {pname}</div>',
            unsafe_allow_html=True,
        )

        data = fetch_notes(pname, api_key, model, store_name, provider)

        if data:
            html = build_html_salla(pname, data, store_name, store_link, store_bio)
            ws.cell(row=row_i + 3, column=desc_col).value = html
            results.append({"name": pname, "ok": True})
            success += 1
        else:
            results.append({"name": pname, "ok": False})
        
        # الانتظار الذكي (منتج بمنتج)
        time.sleep(sleep_time)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf, results, success

def test_api(api_key, model):
    provider = get_api_provider(api_key)
    try:
        if provider == "google":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            body = {"contents": [{"parts": [{"text": "hi"}]}]}
            r = requests.post(url, headers={"Content-Type": "application/json"}, json=body, timeout=10)
        else:
            headers = {"Authorization": f"Bearer {api_key}"}
            body = {"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
            r = requests.post(API_URL_OPENROUTER, headers=headers, json=body, timeout=10)
            
        return r.status_code == 200, f"✅ اتصال ناجح عبر مزود ({provider.upper()})" if r.status_code == 200 else f"Error {r.status_code}"
    except Exception as e:
        return False, str(e)

# ══════════════════════════════════════════════════════════════
#  واجهة التطبيق (UI)
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙️ إعدادات المحرك (API)")
    api_key = st.text_input("مفتاح API (Google أو OpenRouter)", type="password", help="النظام سيتعرف على نوع المفتاح تلقائياً")
    
    model_name = st.selectbox(
        "النموذج (في حال استخدام OpenRouter)", 
        list(MODELS.keys()),
        help="ملاحظة: إذا استخدمت مفتاح Google، سيتم استخدام محرك Gemini 2.0 Flash مباشرة وتجاهل هذا الخيار."
    )
    
    if st.button("🔌 اختبار الاتصال"):
        ok, msg = test_api(api_key, MODELS[model_name])
        if ok: st.success(msg)
        else: st.error(msg)

    st.markdown("---")
    st.markdown("### ⏱️ التحكم بالسرعة")
    sleep_time = st.slider(
        "وقت الانتظار بين المنتجات (ثواني)", 
        min_value=1, max_value=20, value=7,
        help="زيادة الوقت تحمي حسابك المجاني من الحظر (Rate Limit)."
    )

    st.markdown("---")
    st.markdown("### 🏪 بيانات المتجر")
    store_name = st.text_input("اسم المتجر", value="لي غابريال")
    store_link = st.text_input("رابط المتجر", value="https://legabreil.com/ar")
    store_bio = st.text_area(
        "نبذة عن المتجر (ستظهر أسفل كل وصف)",
        value="لأنك تستحق التميز، صممنا في لي غابريال تجربة عطرية لا تُضاهى. نجمع لك بين أصالة الماركات العالمية وسحر عطور النيش في مكان واحد، مع ضمان ذهبي نلتزم به لراحتك وثقتك. نحن هنا لنرافقك في كل مناسباتك بقطرات تعكس شخصيتك المتفردة وحضورك الآسر.",
        height=140
    )

    st.markdown("---")
    st.markdown("### 🎯 خيارات المعالجة")
    process_mode = st.radio(
        "أي المنتجات تريد معالجتها؟",
        ["المنتجات التي ليس لها وصف فقط", "تحديث جميع المنتجات (إعادة كتابة)"],
        index=0
    )
    process_all = (process_mode == "تحديث جميع المنتجات (إعادة كتابة)")

st.title("✨ مولّد أوصاف العطور الاحترافي (الذكاء المزدوج)")
st.info("💡 النظام الآن يدعم مفاتيح Google API المباشرة بشكل مجاني. فقط ضع مفتاحك وحدد وقت الانتظار من الشريط الجانبي لتجنب انقطاع الخدمة.")

uploaded = st.file_uploader("ارفع ملف المنتجات (Excel)", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded, header=1)
    
    total_products = len(df)
    empty_desc = df["الوصف"].apply(is_empty).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 إجمالي المنتجات", total_products)
    c2.metric("📝 بدون وصف", empty_desc)
    
    target_count = total_products if process_all else empty_desc
    c3.metric("🎯 المستهدف للمعالجة", target_count)

    if st.button("🚀 ابدأ المعالجة الآن", type="primary"):
        if not api_key:
            st.error("❌ الرجاء إدخال مفتاح API في الشريط الجانبي")
        elif target_count == 0:
            st.warning("⚠️ لا توجد منتجات للمعالجة بناءً على اختيارك.")
        else:
            bar = st.progress(0)
            status = st.empty()
            
            buf, results, success = process_file(
                uploaded, api_key, MODELS[model_name], 
                store_name, store_link, store_bio, process_all, sleep_time, bar, status
            )
            
            bar.progress(100)
            status.empty()
            
            if success > 0:
                st.success(f"✅ تمت العملية! نجح: {success} | فشل: {len(results)-success}")
                st.download_button(
                    "📥 تحميل الملف الجاهز",
                    data=buf,
                    file_name="products_updated_smart.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error("❌ فشلت معالجة المنتجات. يرجى التأكد من صلاحية مفتاح API أو زيادة وقت الانتظار.")
