import streamlit as st
import pandas as pd
import requests
import json
import time
import io
import re
import openpyxl

# ══════════════════════════════════════════════════════════════
#  مولّد أوصاف عطور | Perfume Description Generator
#  تطبيق عام - يمكن تخصيص اسم المتجر والرابط
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="مولّد أوصاف عطور",
    page_icon="✨",
    layout="wide",
)

# ─── CSS ───
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
.logo-area{text-align:center;padding:10px 0 20px}
.logo-area h2{color:#d4af37;margin:0;font-size:24px}
.logo-area p{color:#999;font-size:12px;margin:4px 0 0}
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

# ─── Helper ───
def is_empty(val) -> bool:
    if pd.isna(val):
        return True
    s = str(val).strip()
    return s in ("", "nan", "<p></p>", "<p><br></p>", "None", "<p> </p>")


def fetch_notes(name: str, api_key: str, model: str) -> dict | None:
    """Get authentic fragrance notes via OpenRouter API."""

    system_msg = """أنت خبير عطور محترف.
مهمتك: البحث عن المكونات الحقيقية والمعلومات الدقيقة للعطور من مصادر موثوقة مثل Fragrantica و Parfumo.
أرجع النتائج بصيغة JSON فقط — بدون أي نص إضافي وبدون backticks وبدون كلمة json."""

    user_msg = f"""ابحث عن العطر التالي وأرجع معلوماته الحقيقية:

اسم المنتج: "{name}"

أرجع JSON بهذا الشكل بالضبط:
{{
  "brand_ar": "اسم الماركة بالعربي",
  "brand_en": "Brand name in English",
  "perfume_en": "Full perfume name in English",
  "year": "سنة الإصدار أو unknown",
  "perfumer": "اسم العطّار أو unknown",
  "family_ar": "العائلة العطرية بالعربي",
  "family_en": "Fragrance family in English",
  "gender": "رجالي أو نسائي أو للجنسين",
  "concentration": "أو دو تواليت أو أو دو بارفيوم أو بارفيوم",
  "concentration_en": "EDT أو EDP أو Parfum",
  "top_ar": "النوتات العليا: وصف تفصيلي بالعربي مع ذكر كل مكون وتأثيره",
  "heart_ar": "نوتات القلب: وصف تفصيلي بالعربي مع ذكر كل مكون وتأثيره",
  "base_ar": "النوتات الأساسية: وصف تفصيلي بالعربي مع ذكر كل مكون وتأثيره",
  "vibe_ar": "وصف الطابع العام للعطر في جملة واحدة",
  "intro_ar": "مقدمة وصفية جذابة بالعربي 2-3 جمل تسويقية عن العطر",
  "season_ar": "الموسم المناسب",
  "occasion_ar": "المناسبات المناسبة"
}}

مهم: استخدم المكونات الحقيقية فقط من Fragrantica. لا تخمّن."""

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
        "temperature": 0.15,
        "max_tokens": 1500,
    }

    try:
        r = requests.post(API_URL, headers=headers, json=body, timeout=120)

        if r.status_code != 200:
            # Show the actual error for debugging
            err_body = r.text[:300]
            st.warning(f"⚠️ API Error {r.status_code} for: {name[:40]}... → {err_body}")
            return None

        text = r.json()["choices"][0]["message"]["content"].strip()

        # Clean markdown fences if present
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?\s*```$", "", text)
        text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError:
        st.warning(f"⚠️ JSON parse error for: {name[:40]}...")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ خطأ اتصال بالإنترنت - تحقق من الشبكة")
        return None
    except requests.exceptions.Timeout:
        st.warning(f"⚠️ انتهت مهلة الطلب: {name[:40]}...")
        return None
    except Exception as e:
        st.warning(f"⚠️ خطأ: {type(e).__name__}: {str(e)[:80]}")
        return None


def build_html(name: str, d: dict, store_name: str, store_link: str) -> str:
    """Build HTML description — NO newlines, NO default longevity.
    
    If store_name/link are empty, no store references are added.
    """

    perfume_en = d.get("perfume_en", "")
    year       = d.get("year", "")
    perfumer   = d.get("perfumer", "")
    family_ar  = d.get("family_ar", "")
    family_en  = d.get("family_en", "")
    gender     = d.get("gender", "")
    conc_ar    = d.get("concentration", "")
    conc_en    = d.get("concentration_en", "")
    top_ar     = d.get("top_ar", "")
    heart_ar   = d.get("heart_ar", "")
    base_ar    = d.get("base_ar", "")
    vibe_ar    = d.get("vibe_ar", "")
    intro_ar   = d.get("intro_ar", "")
    season     = d.get("season_ar", "")
    occasion   = d.get("occasion_ar", "")

    # ─── Size extraction ───
    m = re.search(r"(\d+)\s*مل", name)
    size = m.group(0) if m else ""

    # ─── Detect special types ───
    is_tester = any(k in name for k in ("تستر", "بدون كرتون"))
    is_hair = any(k in name.lower() for k in ("شعر", "hair", "معطر للشعر"))
    ptype_text = "معطر الشعر" if is_hair else f"عطر {gender}" if gender else "عطر"

    # ─── Store link (or empty) ───
    if store_name and store_link:
        a = f'<a href="{store_link}" style="color: #d4af37; font-weight: bold;">{store_name}</a>'
    elif store_name:
        a = f'<strong style="color: #d4af37;">{store_name}</strong>'
    else:
        a = ""

    # ─── Build optional <li> items ───
    opt = ""
    if size:
        opt += f"<li><strong>السعة:</strong> {size}</li>"
    opt += f"<li><strong>نوع المنتج:</strong> {ptype_text}</li>"
    if is_tester:
        opt += "<li><strong>الحالة:</strong> تستر بدون علبة كرتون — المنتج أصلي 100%</li>"
    if conc_ar:
        c_display = f"{conc_ar} ({conc_en})" if conc_en else conc_ar
        opt += f"<li><strong>التركيز:</strong> {c_display}</li>"
    if family_ar:
        f_display = f"{family_ar} ({family_en})" if family_en else family_ar
        opt += f"<li><strong>العائلة العطرية:</strong> {f_display}</li>"
    if perfumer and perfumer.lower() != "unknown":
        opt += f"<li><strong>العطّار:</strong> {perfumer}</li>"
    if year and year.lower() != "unknown":
        opt += f"<li><strong>سنة الإصدار:</strong> {year}</li>"

    en_display = f" ({perfume_en})" if perfume_en else ""

    # ─── INTRO ───
    html = f'<p>اكتشفوا تجربة فريدة من نوعها مع <strong>{name}</strong>، {intro_ar}'
    if a:
        html += f' يقدم لك {a} هذا العطر الفاخر بضمان الأصالة والجودة.'
    html += '</p>'

    # ─── تفاصيل المنتج (h2) ───
    html += (
        '<h2 style="background-color: #f9f9f9; border-right: 5px solid #d4af37; padding: 12px 15px; '
        "font-family: 'Tajawal'; font-size: 20px; color: #333; margin-top: 25px; border-radius: 4px;\">"
        'تفاصيل المنتج</h2>'
        '<ul>'
        f'<li><strong>الاسم:</strong> {name}{en_display}</li>'
        f'{opt}'
    )
    if a:
        html += f'<li><strong>متوفر عبر:</strong> {a}، وجهتك المثالية لكل ما يتعلق بالعطور الفاخرة</li>'
    html += '</ul>'

    # ─── رحلة العطر (h3) ───
    html += (
        '<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; '
        'padding-bottom: 5px; margin-top: 15px; display: inline-block;">'
        'رحلة العطر - النفحات والمكونات</h3>'
        '<ul>'
    )
    if top_ar:
        html += f'<li><strong>النوتات العليا:</strong> {top_ar}</li>'
    if heart_ar:
        html += f'<li><strong>النوتات الوسطى:</strong> {heart_ar}</li>'
    if base_ar:
        html += f'<li><strong>النوتات الأساسية:</strong> {base_ar}</li>'
    if vibe_ar:
        html += f'<li><strong>الطابع العام:</strong> {vibe_ar}</li>'
    html += '</ul>'

    # ─── لماذا تختار (h3) ───
    html += (
        '<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; '
        'padding-bottom: 5px; margin-top: 15px; display: inline-block;">'
        'لماذا تختار هذا العطر؟</h3>'
        '<ul>'
        '<li><strong>تجربة عطرية مميزة:</strong> تركيبة فاخرة من مكونات عطرية مختارة بعناية فائقة تعكس الذوق الرفيع.</li>'
        '<li><strong>ثبات عالي:</strong> تركيبة متوازنة تضمن بقاء العطر لساعات طويلة دون الحاجة لإعادة الرش.</li>'
    )
    if occasion and season:
        html += f'<li><strong>مناسب لـ:</strong> {occasion} في {season}.</li>'
    elif occasion:
        html += f'<li><strong>مناسب لـ:</strong> {occasion}.</li>'
    if is_tester:
        html += '<li><strong>سعر منافس:</strong> تستر أصلي بسعر اقتصادي مثالي للتجربة قبل الشراء.</li>'
    if a:
        html += f'<li><strong>متوفر حصرياً في:</strong> {a} حيث نضمن لك أفضل المنتجات وأعلى مستويات الخدمة.</li>'
    html += '</ul>'

    # ─── الأسئلة الشائعة (h3) ───
    html += (
        '<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; '
        'padding-bottom: 5px; margin-top: 15px; display: inline-block;">'
        'الأسئلة الشائعة</h3>'
        '<ul>'
        '<li><strong>هل العطر مناسب للاستخدام اليومي؟</strong><br>'
        'نعم، العطر متوازن ومناسب للاستخدام اليومي بفضل طابعه الأنيق والمتوازن.</li>'
    )
    if is_tester:
        html += (
            '<li><strong>هل هذا التستر مزود بعلبة كرتون؟</strong><br>'
            'هذا الإصدار يأتي بدون علبة كرتون لتوفير تجربة عطرية أصلية وبسعر اقتصادي.</li>'
        )
    html += (
        '<li><strong>ما مدى ثبات العطر على الجلد؟</strong><br>'
        'يتميز العطر بثبات عالي يدوم لساعات طويلة مع رائحة متجددة طوال اليوم.</li>'
    )
    if a:
        html += (
            f'<li><strong>هل المنتج أصلي؟</strong><br>'
            f'نعم، جميع منتجات {a} أصلية 100% مع ضمان ذهبي للأصالة والجودة.</li>'
        )
    html += '</ul>'

    # ─── CLOSING ───
    html += f'<p>مع <strong>{name}</strong>'
    if a:
        html += f' من {a}،'
    html += ' أنت تضمن تجربة عطرية راقية لا تضاهى مع جودة عالية وضمان الأصالة.'
    if store_name:
        html += f' نحن في <strong>{store_name}</strong> نلتزم بتقديم أفضل العطور الأصلية مع ضمان ذهبي للرضا التام.'
        html += f' اختر التميز، اختر {a}.'
    html += '</p>'

    # CRITICAL: Remove any accidental newlines
    html = html.replace("\n", "").replace("\r", "")

    return html


def process_file(uploaded, api_key, model, store_name, store_link, bar, status):
    """Process Excel: find empty descriptions, generate HTML, save back."""
    raw = uploaded.getvalue()
    wb = openpyxl.load_workbook(io.BytesIO(raw))
    ws = wb.active
    df = pd.read_excel(io.BytesIO(raw), header=1)

    cols = list(df.columns)

    # Find الوصف column
    if "الوصف" not in cols:
        st.error("❌ الملف لا يحتوي على عمود 'الوصف'")
        return None, [], 0

    if "أسم المنتج" not in cols:
        st.error("❌ الملف لا يحتوي على عمود 'أسم المنتج'")
        return None, [], 0

    desc_col = cols.index("الوصف") + 1
    name_col = cols.index("أسم المنتج") + 1

    # Collect empty rows
    tasks = []
    for i, row in df.iterrows():
        if is_empty(row["الوصف"]):
            n = str(row["أسم المنتج"]).strip()
            if n and n != "nan":
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
            f'<div class="product-item">⏳ <strong>({idx+1}/{total})</strong> {pname[:60]}</div>',
            unsafe_allow_html=True,
        )

        notes = fetch_notes(pname, api_key, model)

        if notes:
            html = build_html(pname, notes, store_name, store_link)
            excel_row = row_i + 3  # header offset in openpyxl
            ws.cell(row=excel_row, column=desc_col).value = html
            results.append({"name": pname, "ok": True, "data": notes})
            success += 1
        else:
            results.append({"name": pname, "ok": False, "data": None})

        # Rate limit
        time.sleep(1.5)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf, results, success


def test_api(api_key: str, model: str) -> tuple[bool, str]:
    """Quick test of API connectivity."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://perfume-desc-generator.streamlit.app",
        "X-Title": "Perfume Description Generator",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "قل مرحبا بكلمة واحدة فقط"}],
        "temperature": 0.1,
        "max_tokens": 20,
    }
    try:
        r = requests.post(API_URL, headers=headers, json=body, timeout=30)
        if r.status_code == 200:
            reply = r.json()["choices"][0]["message"]["content"].strip()
            return True, f"✅ الاتصال ناجح! الرد: {reply}"
        else:
            return False, f"❌ خطأ {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"❌ {type(e).__name__}: {str(e)[:150]}"


# ══════════════════════════════════════════════════════════════
#  UI
# ══════════════════════════════════════════════════════════════

# ─── Sidebar ───
with st.sidebar:
    st.markdown("""
    <div class="logo-area">
        <h2>✨ مولّد الأوصاف الذكي</h2>
        <p>Perfume Description Generator</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ إعدادات API")

    api_key = st.text_input(
        "🔑 مفتاح OpenRouter API",
        type="password",
        help="احصل على مفتاح مجاني من openrouter.ai",
    )

    model_name = st.selectbox(
        "🤖 النموذج",
        list(MODELS.keys()),
        index=0,
        help="Gemini Flash مجاني وسريع",
    )
    model_id = MODELS[model_name]

    # Test button
    if api_key:
        if st.button("🔌 اختبار الاتصال", use_container_width=True):
            with st.spinner("جاري الاختبار..."):
                ok, msg = test_api(api_key, model_id)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown("---")
    st.markdown("### 🏪 إعدادات المتجر (اختياري)")

    store_name = st.text_input(
        "اسم المتجر",
        value="",
        placeholder="مثال: لي غابريال",
        help="اتركه فارغاً إذا لم ترد إضافة اسم متجر",
    )
    store_link = st.text_input(
        "رابط المتجر",
        value="",
        placeholder="مثال: https://legabreil.com/ar",
        help="اتركه فارغاً إذا لم ترد إضافة رابط",
    )

    st.markdown("---")
    st.markdown("### 📌 المميزات")
    st.markdown("""
- ✅ مكونات حقيقية من Fragrantica
- ✅ تنسيق HTML متوافق مع سلّة
- ✅ **بدون فراغات** بين الأسطر
- ✅ اسم المتجر والرابط (اختياري)
- ✅ أقسام: تفاصيل، مكونات، FAQ
- ✅ دعم التستر وعطور الشعر
- ✅ **بدون مدة ثبات افتراضية**
    """)

    st.markdown("---")
    st.markdown("### 📋 الخطوات")
    st.markdown("""
1. أدخل مفتاح **OpenRouter API**
2. (اختياري) أدخل اسم المتجر والرابط
3. ارفع ملف **Excel**
4. اضغط **توليد الأوصاف**
5. حمّل الملف المحدّث ✅
    """)

# ─── Main ───
st.markdown("<h1>✨ مولّد أوصاف العطور</h1>", unsafe_allow_html=True)

subtitle = "توليد أوصاف HTML احترافية بمكونات حقيقية — متوافق مع منصة سلّة — بدون فراغات بين الصفوف"
st.markdown(
    f'<p style="text-align:center;color:#888;font-size:15px;margin-top:-10px">{subtitle}</p>',
    unsafe_allow_html=True,
)

# Store info banner
if store_name:
    st.markdown(
        f'<div style="background:#f9f6ec;border-right:5px solid #d4af37;border-radius:8px;'
        f'padding:10px 16px;margin:10px 0;font-size:14px">'
        f'🏪 المتجر: <strong>{store_name}</strong>'
        + (f' | 🔗 <a href="{store_link}" target="_blank">{store_link}</a>' if store_link else "")
        + "</div>",
        unsafe_allow_html=True,
    )

st.markdown("")

# Upload
uploaded = st.file_uploader(
    "📁 ارفع ملف Excel (.xlsx)",
    type=["xlsx", "xls"],
    help="ملف منتجات يحتوي عمود 'أسم المنتج' و 'الوصف'",
)

if uploaded:
    try:
        df_preview = pd.read_excel(uploaded, header=1)
    except Exception as e:
        st.error(f"❌ خطأ في قراءة الملف: {str(e)[:100]}")
        st.stop()

    if "الوصف" not in df_preview.columns or "أسم المنتج" not in df_preview.columns:
        st.error("❌ الملف لا يحتوي على الأعمدة المطلوبة: **أسم المنتج** و **الوصف**")
        st.stop()

    empty_mask = df_preview["الوصف"].apply(is_empty)
    n_empty = int(empty_mask.sum())
    n_total = len(df_preview)
    n_done = n_total - n_empty

    # ─── Stats ───
    st.markdown("")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-num">{n_total:,}</div>'
            f'<div class="stat-label">📦 إجمالي المنتجات</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-card"><div class="stat-num" style="color:#ef4444">{n_empty}</div>'
            f'<div class="stat-label">📝 بدون وصف</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="stat-card"><div class="stat-num" style="color:#22c55e">{n_done:,}</div>'
            f'<div class="stat-label">✅ مكتملة</div></div>',
            unsafe_allow_html=True,
        )

    if n_empty > 0:
        # ─── List empty products ───
        st.markdown("")
        with st.expander(f"👁️ عرض المنتجات بدون وصف ({n_empty} منتج)", expanded=True):
            empties = df_preview[empty_mask][["أسم المنتج", "سعر المنتج"]].reset_index(drop=True)
            for i, row in empties.iterrows():
                price = row["سعر المنتج"]
                price_str = f"{price:,.2f} ر.س" if pd.notna(price) else ""
                st.markdown(
                    f'<div class="product-item">'
                    f"<strong>{i+1}.</strong> {row['أسم المنتج']} — {price_str}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # ─── Generate button ───
        st.markdown("")
        if st.button("🪄 توليد الأوصاف الآن", use_container_width=True):
            if not api_key:
                st.error("❌ الرجاء إدخال مفتاح OpenRouter API في الشريط الجانبي")
            else:
                st.markdown("---")
                bar = st.progress(0)
                status = st.empty()

                buf, results, ok_count = process_file(
                    uploaded, api_key, model_id, store_name, store_link, bar, status
                )

                if buf:
                    bar.progress(1.0)
                    fail_count = len(results) - ok_count
                    status.empty()

                    if ok_count > 0:
                        st.markdown(
                            f'<div class="done-box">'
                            f'<h2 style="color:#22c55e;margin:0">✅ تم بنجاح!</h2>'
                            f'<p style="font-size:20px;margin:10px 0">'
                            f"نجح: <strong>{ok_count}</strong> &nbsp;|&nbsp; "
                            f"فشل: <strong>{fail_count}</strong></p></div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<div class="fail-box">'
                            '<h2 style="color:#ef4444;margin:0">❌ فشلت جميع المحاولات</h2>'
                            "<p>تحقق من مفتاح API والنموذج المختار — جرّب زر اختبار الاتصال</p></div>",
                            unsafe_allow_html=True,
                        )

                    # Detailed results
                    with st.expander("📋 تفاصيل النتائج"):
                        for r in results:
                            icon = "✅" if r["ok"] else "❌"
                            st.markdown(f"**{icon}** {r['name'][:70]}")
                            if r.get("data"):
                                dd = r["data"]
                                st.caption(
                                    f"🏷️ {dd.get('family_ar', '')} | "
                                    f"{dd.get('top_ar', '')[:50]}..."
                                )

                    # Download
                    st.markdown("")
                    st.download_button(
                        "📥 تحميل الملف المحدّث",
                        data=buf,
                        file_name="منتجات_محدثة.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                else:
                    st.info("✅ جميع المنتجات مكتملة بالفعل!")
    else:
        st.markdown("")
        st.success("🎉 ممتاز! جميع المنتجات تحتوي على أوصاف بالفعل.")


# ─── Preview ───
st.markdown("---")
with st.expander("👁️ معاينة تنسيق الوصف النهائي"):
    preview_store = store_name if store_name else "اسم المتجر"
    preview_link = store_link if store_link else "#"
    pa = f'<a href="{preview_link}" style="color: #d4af37; font-weight: bold;">{preview_store}</a>'

    st.markdown(f"""
<div style="background:#fafafa;padding:20px;border-radius:10px;direction:rtl;line-height:1.9">
<p>اكتشفوا تجربة فريدة مع <strong>اسم العطر</strong>، مقدمة وصفية جذابة...
يقدم لك {pa} هذا العطر الفاخر.</p>
<h2 style="background:#f9f9f9;border-right:5px solid #d4af37;padding:12px 15px;
font-size:20px;color:#333;border-radius:4px">تفاصيل المنتج</h2>
<ul><li><strong>الاسم:</strong> العطر (English Name)</li>
<li><strong>العائلة العطرية:</strong> شرقي خشبي (Oriental Woody)</li></ul>
<h3 style="font-size:18px;color:#d4af37;border-bottom:1px solid #eee;
padding-bottom:5px;display:inline-block">رحلة العطر - النفحات والمكونات</h3>
<ul><li><strong>النوتات العليا:</strong> مكونات حقيقية...</li>
<li><strong>النوتات الوسطى:</strong> مكونات حقيقية...</li>
<li><strong>النوتات الأساسية:</strong> مكونات حقيقية...</li></ul>
<h3 style="font-size:18px;color:#d4af37;border-bottom:1px solid #eee;
padding-bottom:5px;display:inline-block">لماذا تختار هذا العطر؟</h3>
<h3 style="font-size:18px;color:#d4af37;border-bottom:1px solid #eee;
padding-bottom:5px;display:inline-block">الأسئلة الشائعة</h3>
</div>
    """, unsafe_allow_html=True)

# Footer
st.markdown(
    '<p style="text-align:center;color:#ccc;font-size:11px;margin-top:40px">'
    "✨ مولّد أوصاف العطور | مكونات حقيقية | متوافق مع سلّة | بدون فراغات"
    "</p>",
    unsafe_allow_html=True,
)
