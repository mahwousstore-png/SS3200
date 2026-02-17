import streamlit as st
import pandas as pd
import requests
import json
import time
import io
import re
import openpyxl

# ══════════════════════════════════════════════════════════════
#  مولّد أوصاف عطور لي غابريال | Le Gabriel Perfume Description Generator
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="مولّد أوصاف عطور | لي غابريال",
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
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stSelectbox label{direction:rtl;text-align:right}
h1{text-align:center!important;background:linear-gradient(135deg,#d4af37,#b8960c);
   -webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.2rem!important}
.stButton>button{
    background:linear-gradient(135deg,#d4af37 0%,#c5a028 50%,#b8960c 100%);
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
.preview-box{
    background:#fafafa;border:1px solid #eee;border-radius:12px;
    padding:24px;direction:rtl;line-height:1.9
}
.preview-box h2{
    background-color:#f9f9f9;border-right:5px solid #d4af37;
    padding:12px 15px;font-size:20px;color:#333;margin-top:25px;border-radius:4px
}
.preview-box h3{
    font-size:18px;color:#d4af37;border-bottom:1px solid #eee;
    padding-bottom:5px;margin-top:15px;display:inline-block
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───
API_URL = "https://openrouter.ai/api/v1/chat/completions"
STORE   = "لي غابريال"
LINK    = "https://legabreil.com/ar"

MODELS = {
    "Gemini 2.0 Flash (سريع ومجاني)": "google/gemini-2.0-flash-001",
    "Gemini 2.5 Flash": "google/gemini-2.5-flash-preview",
    "Claude Sonnet 4": "anthropic/claude-sonnet-4",
    "GPT-4o Mini": "openai/gpt-4o-mini",
}

# ─── Utility ───
def is_empty(val) -> bool:
    if pd.isna(val):
        return True
    s = str(val).strip()
    return s in ("", "nan", "<p></p>", "<p><br></p>", "None", "<p> </p>")


def fetch_notes(name: str, api_key: str, model: str) -> dict | None:
    """Get authentic fragrance notes via OpenRouter API."""

    system = """أنت خبير عطور محترف تعمل مع متجر لي غابريال للعطور الأصلية.
مهمتك: البحث عن المكونات الحقيقية والمعلومات الدقيقة للعطور من مصادر موثوقة مثل Fragrantica و Parfumo.
أرجع النتائج بصيغة JSON فقط بدون أي نص إضافي أو backticks."""

    prompt = f"""ابحث عن العطر التالي وأرجع معلوماته الحقيقية بصيغة JSON:

اسم المنتج: "{name}"

أرجع JSON بالضبط بهذا الشكل:
{{
  "brand_ar": "اسم الماركة بالعربي",
  "brand_en": "اسم الماركة بالإنجليزي",
  "perfume_ar": "اسم العطر بالعربي",
  "perfume_en": "اسم العطر بالإنجليزي",
  "year": "سنة الإصدار أو unknown",
  "perfumer": "اسم العطّار أو unknown",
  "family_ar": "العائلة العطرية بالعربي مثل: فوجير خشبي أو شرقي زهري",
  "family_en": "Woody Floral Musk",
  "gender": "رجالي أو نسائي أو للجنسين",
  "concentration": "أو دو تواليت أو أو دو بارفيوم أو بارفيوم",
  "concentration_en": "EDT أو EDP أو Parfum",
  "top_ar": "وصف النوتات العليا بالعربي مع ذكر كل مكون ووصف قصير لتأثيره - مثال: مزيج منعش من البرغموت والليمون والخزامى يفتح العطر بانطلاقة حيوية ونظيفة",
  "heart_ar": "وصف نوتات القلب بالعربي بنفس الأسلوب الوصفي مع ذكر كل مكون",
  "base_ar": "وصف النوتات الأساسية بالعربي بنفس الأسلوب مع ذكر كل مكون",
  "vibe_ar": "وصف الطابع العام للعطر في جملتين: متى يناسب ولمن يناسب",
  "intro_ar": "فقرة تعريفية جذابة بالعربي 2-3 جمل تصف العطر وتاريخه وطابعه بأسلوب تسويقي راقي",
  "longevity": "ثبات العطر مثلاً: من 6 إلى 8 ساعات",
  "season_ar": "الموسم المناسب مثلاً: جميع الفصول أو الشتاء والخريف",
  "occasion_ar": "المناسبات مثلاً: المناسبات الرسمية والمسائية"
}}

مهم جداً:
- استخدم المكونات الحقيقية من Fragrantica فقط
- لا تخمّن أو تفترض مكونات غير صحيحة
- اكتب بأسلوب عربي تسويقي راقي
- أرجع JSON فقط بدون أي نص آخر"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.15,
        "max_tokens": 1500,
    }

    try:
        r = requests.post(API_URL, headers=headers, json=body, timeout=120)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip()
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
        return json.loads(text)
    except json.JSONDecodeError as je:
        st.warning(f"⚠️ خطأ JSON: {str(je)[:80]}")
        return None
    except requests.exceptions.RequestException as re_err:
        st.error(f"❌ خطأ اتصال: {str(re_err)[:100]}")
        return None
    except Exception as e:
        st.warning(f"⚠️ خطأ: {str(e)[:100]}")
        return None


def build_html(name: str, d: dict) -> str:
    """Build HTML exactly matching Le Gabriel / Salla format.
    
    CRITICAL: Output is ONE continuous line — NO newlines whatsoever.
    Uses h2 for first section, h3 for rest (matching sample_description.html).
    """

    # Extract data with fallbacks
    brand_ar   = d.get("brand_ar", "")
    brand_en   = d.get("brand_en", "")
    perfume_ar = d.get("perfume_ar", name)
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
    longevity  = d.get("longevity", "من 6 إلى 8 ساعات")
    season     = d.get("season_ar", "جميع الفصول")
    occasion   = d.get("occasion_ar", "المناسبات المختلفة")

    # Size
    m = re.search(r"(\d+)\s*مل", name)
    size = m.group(0) if m else ""

    # Tester
    is_tester = any(k in name for k in ("تستر", "بدون كرتون"))

    # Hair mist
    is_hair = any(k in name.lower() for k in ("شعر", "hair", "معطر"))
    ptype_text = "عطر الشعر" if is_hair else f"عطر {gender}" if gender else "عطر"

    # Link shorthand
    a = f'<a href="{LINK}" style="color: #d4af37; font-weight: bold;">{STORE}</a>'

    # Build optional <li> items
    opt = ""
    if size:
        opt += f"<li><strong>السعة:</strong> {size}</li>"
    opt += f"<li><strong>نوع المنتج:</strong> {ptype_text}</li>"
    if is_tester:
        opt += "<li><strong>الحالة:</strong> تستر بدون علبة كرتون</li>"
    if conc_ar:
        conc_display = f"{conc_ar} ({conc_en})" if conc_en else conc_ar
        opt += f"<li><strong>التركيز:</strong> {conc_display}</li>"
    if family_ar:
        fam_display = f"{family_ar} ({family_en})" if family_en else family_ar
        opt += f"<li><strong>العائلة العطرية:</strong> {fam_display}</li>"
    if perfumer and perfumer.lower() != "unknown":
        opt += f"<li><strong>العطّار:</strong> {perfumer}</li>"
    if year and year.lower() != "unknown":
        opt += f"<li><strong>سنة الإصدار:</strong> {year}</li>"

    # English name for display
    en_display = f" ({perfume_en})" if perfume_en else ""

    # ─── INTRO PARAGRAPH ───
    html = (
        f'<p>اكتشفوا تجربة فريدة من نوعها مع <strong>{name}</strong>، '
        f'{intro_ar} '
        f'يقدم لك {a} هذا العطر الفاخر بضمان الأصالة والجودة.</p>'
    )

    # ─── تفاصيل المنتج (h2) ───
    html += (
        f'<h2 style="background-color: #f9f9f9; border-right: 5px solid #d4af37; padding: 12px 15px; '
        f"font-family: 'Tajawal'; font-size: 20px; color: #333; margin-top: 25px; border-radius: 4px;\">"
        f'تفاصيل المنتج</h2>'
        f'<ul>'
        f'<li><strong>الاسم:</strong> {name}{en_display}</li>'
        f'{opt}'
        f'<li><strong>متوفر عبر:</strong> {a}، وجهتك المثالية لكل ما يتعلق بالعطور الفاخرة</li>'
        f'</ul>'
    )

    # ─── رحلة العطر (h3) ───
    html += (
        f'<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; '
        f'padding-bottom: 5px; margin-top: 15px; display: inline-block;">'
        f'رحلة العطر - النفحات والمكونات</h3>'
        f'<ul>'
        f'<li><strong>النوتات العليا:</strong> {top_ar}</li>'
        f'<li><strong>النوتات الوسطى:</strong> {heart_ar}</li>'
        f'<li><strong>النوتات الأساسية:</strong> {base_ar}</li>'
    )
    if vibe_ar:
        html += f'<li><strong>الطابع العام:</strong> {vibe_ar}</li>'
    html += '</ul>'

    # ─── لماذا تختار (h3) ───
    html += (
        f'<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; '
        f'padding-bottom: 5px; margin-top: 15px; display: inline-block;">'
        f'لماذا تختار هذا العطر؟</h3>'
        f'<ul>'
        f'<li><strong>تجربة عطرية مميزة:</strong> تركيبة فاخرة من مكونات عطرية مختارة بعناية فائقة تعكس الذوق الرفيع.</li>'
        f'<li><strong>ثبات عالي:</strong> يدوم {longevity} على البشرة مع انتشار أنيق ومتوازن لا يزعج المحيطين.</li>'
        f'<li><strong>مناسب لـ:</strong> {occasion} في {season}.</li>'
    )
    if is_tester:
        html += '<li><strong>سعر منافس:</strong> تستر أصلي بسعر اقتصادي مثالي للتجربة قبل الشراء.</li>'
    html += (
        f'<li><strong>متوفر حصرياً في:</strong> {a} حيث نضمن لك أفضل المنتجات وأعلى مستويات الخدمة.</li>'
        f'</ul>'
    )

    # ─── الأسئلة الشائعة (h3) ───
    html += (
        f'<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; '
        f'padding-bottom: 5px; margin-top: 15px; display: inline-block;">'
        f'الأسئلة الشائعة</h3>'
        f'<ul>'
        f'<li><strong>هل العطر مناسب للاستخدام اليومي؟</strong><br>'
        f'نعم، العطر متوازن ومناسب لـ{occasion} بفضل طابعه الأنيق والمتوازن.</li>'
    )
    if is_tester:
        html += (
            f'<li><strong>هل هذا التستر مزود بعلبة كرتون؟</strong><br>'
            f'هذا الإصدار يأتي بدون علبة كرتون لتوفير تجربة عطرية أصلية وبسعر اقتصادي.</li>'
        )
    html += (
        f'<li><strong>ما مدى ثبات العطر على الجلد؟</strong><br>'
        f'يتميز العطر بثبات عالي يدوم {longevity} مع رائحة متجددة.</li>'
        f'<li><strong>هل المنتج أصلي؟</strong><br>'
        f'نعم، جميع منتجات {a} أصلية 100% مع ضمان ذهبي للأصالة والجودة.</li>'
        f'</ul>'
    )

    # ─── CLOSING ───
    html += (
        f'<p>مع <strong>{name}</strong> من {a}، '
        f'أنت تضمن تجربة عطرية راقية لا تضاهى مع جودة عالية وضمان الأصالة. '
        f'نحن في <strong>{STORE}</strong> نلتزم بتقديم أفضل العطور الأصلية مع ضمان ذهبي للرضا التام. '
        f'اختر التميز، اختر {a}.</p>'
    )

    # CRITICAL: Remove any accidental newlines
    html = html.replace("\n", "").replace("\r", "")

    return html


def process_file(uploaded, api_key, model, bar, status):
    """Process Excel: find empty descriptions, generate HTML, save back."""
    raw = uploaded.getvalue()
    wb = openpyxl.load_workbook(io.BytesIO(raw))
    ws = wb.active
    df = pd.read_excel(io.BytesIO(raw), header=1)

    cols = list(df.columns)
    desc_col = cols.index("الوصف") + 1  # 1-based for openpyxl
    name_col = cols.index("أسم المنتج") + 1

    # Find empty rows
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
            unsafe_allow_html=True
        )

        notes = fetch_notes(pname, api_key, model)

        if notes:
            html = build_html(pname, notes)
            # Write to Excel — row_i is 0-based df index
            # Header is row 1-2 in Excel, data starts row 3
            excel_row = row_i + 3
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


# ══════════════════════════════════════════════════════════════
#  UI
# ══════════════════════════════════════════════════════════════

# ─── Sidebar ───
with st.sidebar:
    st.markdown("""
    <div class="logo-area">
        <h2>✨ لي غابريال</h2>
        <p>Le Gabriel | مولّد الأوصاف الذكي</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ الإعدادات")

    api_key = st.text_input(
        "🔑 مفتاح OpenRouter API",
        type="password",
        help="أدخل مفتاح API من openrouter.ai"
    )

    model_name = st.selectbox(
        "🤖 نموذج الذكاء الاصطناعي",
        list(MODELS.keys()),
        index=0,
        help="اختر النموذج المستخدم لتوليد الأوصاف"
    )
    model_id = MODELS[model_name]

    st.markdown("---")
    st.markdown("### 📌 المميزات")
    st.markdown("""
- ✅ مكونات حقيقية من Fragrantica
- ✅ تنسيق HTML متوافق مع سلّة
- ✅ **بدون فراغات** بين الأسطر
- ✅ روابط ذهبية لـ legabreil.com
- ✅ أقسام: تفاصيل، مكونات، FAQ
- ✅ دعم التستر وعطور الشعر
- ✅ ثبات، موسم، مناسبات
    """)

    st.markdown("---")
    st.markdown("### 📋 خطوات الاستخدام")
    st.markdown("""
1. أدخل مفتاح **OpenRouter API**
2. ارفع ملف **غبريال تحديث.xlsx**
3. اضغط **توليد الأوصاف**
4. حمّل الملف المحدّث ✅
    """)

    st.markdown("---")
    st.markdown(
        '<p style="color:#bbb;font-size:11px;text-align:center">'
        'legabreil.com | مكونات حقيقية | سلّة</p>',
        unsafe_allow_html=True
    )

# ─── Main ───
st.markdown("<h1>✨ مولّد أوصاف عطور لي غابريال</h1>", unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;color:#888;font-size:15px;margin-top:-10px">'
    'توليد أوصاف HTML احترافية بمكونات حقيقية — متوافق مع منصة سلّة — بدون فراغات بين الصفوف'
    '</p>',
    unsafe_allow_html=True
)

st.markdown("")

# Upload
uploaded = st.file_uploader(
    "📁 ارفع ملف Excel — غبريال تحديث.xlsx",
    type=["xlsx", "xls"],
    help="ارفع ملف المنتجات من لوحة تحكم سلّة"
)

if uploaded:
    df_preview = pd.read_excel(uploaded, header=1)

    if "الوصف" not in df_preview.columns or "أسم المنتج" not in df_preview.columns:
        st.error("❌ الملف لا يحتوي على الأعمدة المطلوبة: 'أسم المنتج' و 'الوصف'")
        st.stop()

    empty_mask = df_preview["الوصف"].apply(is_empty)
    n_empty = int(empty_mask.sum())
    n_total = len(df_preview)
    n_done  = n_total - n_empty

    # ─── Stats ───
    st.markdown("")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-num">{n_total:,}</div>'
            f'<div class="stat-label">📦 إجمالي المنتجات</div></div>',
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-num" style="color:#ef4444">{n_empty}</div>'
            f'<div class="stat-label">📝 بدون وصف</div></div>',
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-num" style="color:#22c55e">{n_done:,}</div>'
            f'<div class="stat-label">✅ مكتملة</div></div>',
            unsafe_allow_html=True
        )

    if n_empty > 0:
        # ─── Empty products list ───
        st.markdown("")
        with st.expander(f"👁️ عرض المنتجات بدون وصف ({n_empty} منتج)", expanded=True):
            empties = df_preview[empty_mask][["أسم المنتج", "سعر المنتج"]].reset_index(drop=True)
            for i, row in empties.iterrows():
                price = row["سعر المنتج"]
                price_str = f"{price:,.2f} ر.س" if pd.notna(price) else ""
                st.markdown(
                    f'<div class="product-item">'
                    f'<strong>{i+1}.</strong> {row["أسم المنتج"]} — {price_str}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # ─── Generate button ───
        st.markdown("")
        if st.button("🪄 توليد الأوصاف الآن", use_container_width=True):
            if not api_key:
                st.error("❌ الرجاء إدخال مفتاح OpenRouter API في الإعدادات الجانبية")
            else:
                st.markdown("---")
                bar = st.progress(0)
                status = st.empty()

                buf, results, ok_count = process_file(
                    uploaded, api_key, model_id, bar, status
                )

                if buf:
                    bar.progress(1.0)
                    fail_count = len(results) - ok_count
                    status.empty()

                    # ─── Success summary ───
                    if ok_count > 0:
                        st.markdown(
                            f'<div class="done-box">'
                            f'<h2 style="color:#22c55e;margin:0">✅ تم بنجاح!</h2>'
                            f'<p style="font-size:20px;margin:10px 0">'
                            f'نجح: <strong>{ok_count}</strong> &nbsp;|&nbsp; '
                            f'فشل: <strong>{fail_count}</strong></p>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="fail-box">'
                            f'<h2 style="color:#ef4444;margin:0">❌ فشلت جميع المحاولات</h2>'
                            f'<p>تحقق من مفتاح API والنموذج المختار</p>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                    # ─── Detailed results ───
                    with st.expander("📋 تفاصيل النتائج"):
                        for r in results:
                            icon = "✅" if r["ok"] else "❌"
                            st.markdown(f"**{icon}** {r['name'][:70]}")
                            if r.get("data"):
                                dd = r["data"]
                                st.caption(
                                    f"🏷️ {dd.get('family_ar','')} | "
                                    f"العليا: {dd.get('top_ar','')[:60]}..."
                                )

                    # ─── Download ───
                    st.markdown("")
                    st.download_button(
                        "📥 تحميل الملف المحدّث — غبريال_تحديث_مكتمل.xlsx",
                        data=buf,
                        file_name="غبريال_تحديث_مكتمل.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                else:
                    st.info("✅ جميع المنتجات مكتملة بالفعل!")

    else:
        st.markdown("")
        st.success("🎉 ممتاز! جميع المنتجات تحتوي على أوصاف بالفعل.")

# ─── Preview section ───
st.markdown("---")
with st.expander("👁️ معاينة تنسيق الوصف النهائي"):
    sample_link = f'<a href="{LINK}" style="color: #d4af37; font-weight: bold;">{STORE}</a>'
    st.markdown(f"""
<div class="preview-box">
<p>اكتشفوا تجربة فريدة من نوعها مع <strong>اسم العطر الكامل</strong>،
مقدمة وصفية جذابة عن العطر وتاريخه...
يقدم لك {sample_link} هذا العطر الفاخر بضمان الأصالة والجودة.</p>

<h2>تفاصيل المنتج</h2>
<ul>
<li><strong>الاسم:</strong> اسم العطر (English Name)</li>
<li><strong>السعة:</strong> 100 مل</li>
<li><strong>العائلة العطرية:</strong> شرقي خشبي (Oriental Woody)</li>
<li><strong>العطّار:</strong> اسم العطّار</li>
</ul>

<h3>رحلة العطر - النفحات والمكونات</h3>
<ul>
<li><strong>النوتات العليا:</strong> وصف المكونات الحقيقية من Fragrantica...</li>
<li><strong>النوتات الوسطى:</strong> وصف المكونات الحقيقية...</li>
<li><strong>النوتات الأساسية:</strong> وصف المكونات الحقيقية...</li>
</ul>

<h3>لماذا تختار هذا العطر؟</h3>
<ul>
<li><strong>ثبات عالي:</strong> يدوم من 6 إلى 8 ساعات...</li>
<li><strong>متوفر حصرياً في:</strong> {sample_link}</li>
</ul>

<h3>الأسئلة الشائعة</h3>
<ul>
<li><strong>هل المنتج أصلي؟</strong><br>نعم، جميع منتجات {sample_link} أصلية 100%</li>
</ul>

<p>اختر التميز، اختر {sample_link}.</p>
</div>
    """, unsafe_allow_html=True)

# Footer
st.markdown(
    '<p style="text-align:center;color:#ccc;font-size:11px;margin-top:40px">'
    '✨ مولّد أوصاف لي غابريال | مكونات حقيقية من Fragrantica | متوافق مع منصة سلّة | بدون فراغات'
    '</p>',
    unsafe_allow_html=True
)
