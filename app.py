import streamlit as st
import pandas as pd
import json
import time
import io
import re
import openpyxl
import asyncio
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import base64

# ══════════════════════════════════════════════════════════════
#  معالج أوصاف العطور - النسخة الشاملة (3200+ منتج)
#  يعالج كل المنتجات بما فيها التي لها أوصاف
# ══════════════════════════════════════════════════════════════

st.set_page_config(page_title="معالج أوصاف العطور | شامل", page_icon="⚡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
*{font-family:'Tajawal',sans-serif}
[data-testid="stAppViewContainer"]{direction:rtl;text-align:right}
[data-testid="stSidebar"]{direction:rtl;text-align:right}
.dash-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
.dash-title { font-size: 15px; color: #64748b; margin-bottom: 5px; }
.dash-value { font-size: 30px; font-weight: bold; color: #d4af37; }
.log-box { background: #1e293b; color: #10b981; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 13px; direction: ltr; text-align: left; height: 160px; overflow-y: auto; }
.info-box { background: #eff6ff; border: 1px solid #bfdbfe; padding: 12px 16px; border-radius: 8px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

API_URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

# ─── دوال المساعدة ───
def is_empty(val) -> bool:
    if pd.isna(val):
        return True
    return str(val).strip() in ("", "nan", "<p></p>", "<p><br></p>", "None", "<p> </p>")

# ─── بناء HTML لسلة ───
def build_simple_salla_html(name: str, d: dict, store_name: str, store_link: str) -> str:
    if store_link:
        a_tag = f'<a href="{store_link}" style="color:#d4af37;font-weight:bold;text-decoration:none;">{store_name}</a>'
    else:
        a_tag = f'<strong style="color:#d4af37;">{store_name}</strong>'

    m = re.search(r"(\d+)\s*مل", name)
    size = m.group(0) if m else "حسب الاختيار"

    h2_style = "background:#f9f9f9;border-right:4px solid #d4af37;padding:8px 12px;font-size:18px;color:#333;margin:20px 0 10px;border-radius:3px;"
    h3_style = "font-size:16px;color:#d4af37;border-bottom:1px solid #eee;padding-bottom:5px;margin:15px 0 10px;display:inline-block;"
    ul_style = "padding-right:20px;margin-bottom:15px;font-size:15px;"

    html = f"""<div style="font-family:'Tajawal',sans-serif;color:#333;line-height:1.8;text-align:right;direction:rtl;">
<p style="margin-bottom:15px;">{d.get('intro_paragraph', '')} يقدم لك {a_tag} هذا العطر الفاخر لتكتمل أناقتك.</p>
<h2 style="{h2_style}">تفاصيل المنتج</h2>
<ul style="{ul_style}">
<li><strong>الاسم:</strong> {d.get('perfume_ar', name)} ({d.get('perfume_en', '')})</li>
<li><strong>السعة:</strong> {size}</li>
<li><strong>التركيز:</strong> {d.get('concentration', '')}</li>
<li><strong>العائلة العطرية:</strong> {d.get('family', '')}</li>
<li><strong>متوفر عبر:</strong> {a_tag}</li>
</ul>
<h3 style="{h3_style}">رحلة العطر</h3>
<ul style="{ul_style}">
<li><strong>الافتتاحية:</strong> {d.get('top_notes', '')}</li>
<li><strong>القلب:</strong> {d.get('heart_notes', '')}</li>
<li><strong>القاعدة:</strong> {d.get('base_notes', '')}</li>
<li><strong>الطابع العام:</strong> {d.get('general_vibe', '')}</li>
</ul>
<h3 style="{h3_style}">لماذا هذا العطر؟</h3>
<ul style="{ul_style}">
<li><strong>التميز:</strong> {d.get('why_choose_1', '')}</li>
<li><strong>الجودة:</strong> {d.get('why_choose_2', '')}</li>
</ul>
<h3 style="{h3_style}">الأسئلة الشائعة</h3>
<ul style="{ul_style}">
<li><strong>{d.get('faq_1_q', 'هل العطر مناسب للاستخدام اليومي؟')}</strong><br>{d.get('faq_1_a', '')}</li>
<li><strong>{d.get('faq_3_q', 'ما مدى الثبات؟')}</strong><br>{d.get('faq_3_a', '')}</li>
</ul>
<p>{d.get('closing_paragraph', '')} اختر {a_tag}.</p></div>"""

    return re.sub(r'\s{2,}', ' ', html.replace("\n", "").replace("\r", ""))

# ─── محرك الذكاء الاصطناعي ───
@retry(wait=wait_exponential(multiplier=1, min=4, max=15), stop=stop_after_attempt(4), retry=retry_if_exception_type(Exception))
async def fetch_notes_async(session, name: str, api_key: str, model: str, store_name: str, semaphore):
    system_msg = """أنت خبير محتوى وتسويق عطور. أرجع وصفاً شاملاً ومفصلاً (أكثر من 2000 حرف) كـ JSON فقط وبدون أي إضافات:
{"perfume_en":"","perfume_ar":"","concentration":"","family":"","intro_paragraph":"","top_notes":"","heart_notes":"","base_notes":"","general_vibe":"","why_choose_1":"","why_choose_2":"","faq_1_q":"","faq_1_a":"","faq_3_q":"","faq_3_a":"","closing_paragraph":""}"""
    user_msg = f'اكتب وصفاً احترافياً للمنتج: "{name}" لمتجر "{store_name}".'

    async with semaphore:
        try:
            if api_key.startswith("AIza"):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                body = {
                    "contents": [{"role": "user", "parts": [{"text": system_msg + "\n\n" + user_msg}]}],
                    "generationConfig": {"temperature": 0.4}
                }
                async with session.post(url, headers={"Content-Type": "application/json"}, json=body) as res:
                    if res.status == 200:
                        data = await res.json()
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                    elif res.status == 429:
                        await asyncio.sleep(10)
                        raise Exception(f"Rate limit 429")
                    else:
                        raise Exception(f"Gemini API error: {res.status}")
            else:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                body = {"model": model, "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]}
                async with session.post(API_URL_OPENROUTER, headers=headers, json=body) as res:
                    if res.status == 200:
                        data = await res.json()
                        text = data["choices"][0]["message"]["content"]
                    elif res.status == 429:
                        await asyncio.sleep(10)
                        raise Exception(f"Rate limit 429")
                    else:
                        raise Exception(f"OpenRouter API error: {res.status}")

            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            raise ValueError("No valid JSON found")
        except Exception as e:
            raise

# ─── معالجة منتج واحد ───
async def process_product(session, row_i, pname, active_keys, idx, model, store_name, store_link, semaphore, ws, desc_col):
    key = active_keys[idx % len(active_keys)]
    try:
        data = await fetch_notes_async(session, pname, key, model, store_name, semaphore)
        if data:
            html = build_simple_salla_html(pname, data, store_name, store_link)
            ws.cell(row=row_i + 3, column=desc_col).value = html
            return {"name": pname, "ok": True}
    except Exception as e:
        pass
    return {"name": pname, "ok": False}

# ─── تشغيل المهام ───
async def run_background_job(tasks, active_keys, model, store_name, store_link, limit, ui_components, ws, desc_col, save_interval, wb, filename):
    semaphore = asyncio.Semaphore(limit)
    total = len(tasks)
    completed = 0
    success = 0
    failed = 0
    log_messages = []
    start_time = time.time()
    last_save = 0

    async with aiohttp.ClientSession() as session:
        coroutines = [
            process_product(session, r, p, active_keys, i, model, store_name, store_link, semaphore, ws, desc_col)
            for i, (r, p) in enumerate(tasks)
        ]

        for future in asyncio.as_completed(coroutines):
            res = await future
            completed += 1
            if res["ok"]:
                success += 1
            else:
                failed += 1

            ui_components['prog'].progress(completed / total)
            ui_components['comp'].markdown(f"<div class='dash-value'>{completed} / {total}</div>", unsafe_allow_html=True)
            ui_components['succ'].markdown(f"<div class='dash-value' style='color:#10b981;'>{success}</div>", unsafe_allow_html=True)
            ui_components['fail'].markdown(f"<div class='dash-value' style='color:#ef4444;'>{failed}</div>", unsafe_allow_html=True)

            elapsed = time.time() - start_time
            if completed > 0:
                avg = elapsed / completed
                remaining = total - completed
                eta = int(avg * remaining)
                h, m_, s = eta // 3600, (eta % 3600) // 60, eta % 60
                eta_str = f"{h:02d}:{m_:02d}:{s:02d}" if h > 0 else f"{m_:02d}:{s:02d}"
                ui_components['eta'].markdown(f"<div class='dash-value'>{eta_str}</div>", unsafe_allow_html=True)

            log_messages.insert(0, f"[{completed}/{total}] {'✅' if res['ok'] else '❌'} {res['name'][:45]}")
            if len(log_messages) > 6:
                log_messages.pop()
            ui_components['log'].markdown(f"<div class='log-box'>{'<br>'.join(log_messages)}</div>", unsafe_allow_html=True)

            # حفظ تلقائي دوري
            if completed - last_save >= save_interval:
                buf = io.BytesIO()
                wb.save(buf)
                buf.seek(0)
                b64 = base64.b64encode(buf.read()).decode()
                link = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" style="display:block;text-align:center;background:#3b82f6;color:white;padding:10px;border-radius:8px;text-decoration:none;font-weight:bold;margin:5px 0;">💾 حفظ جزئي ({completed}/{total})</a>'
                ui_components['save'].markdown(link, unsafe_allow_html=True)
                last_save = completed

    return success

def get_download_link(wb, filename="Salla_All_Products.xlsx"):
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" style="display:block;text-align:center;background:#10b981;color:white;padding:18px;border-radius:12px;text-decoration:none;font-size:22px;font-weight:bold;margin:20px 0;">📥 تحميل الملف الكامل المكتمل</a>'

# ─── واجهة المستخدم ───
with st.sidebar:
    st.markdown("### 🔑 مفاتيح API")
    keys_input = st.text_area("كل مفتاح في سطر:", height=120, placeholder="AIza... أو مفتاح OpenRouter")
    active_keys = [k.strip() for k in keys_input.split('\n') if k.strip()]
    
    st.markdown("---")
    st.markdown("### ⚙️ الإعدادات")
    model_name = st.selectbox("النموذج", [
        "google/gemini-2.0-flash-001",
        "google/gemini-flash-1.5",
        "openai/gpt-4o-mini",
        "anthropic/claude-3-haiku"
    ])
    concurrency = st.slider("طلبات متزامنة:", 3, 25, 10, help="قلل إذا واجهت أخطاء Rate Limit")
    save_every = st.slider("حفظ تلقائي كل (منتج):", 50, 500, 200)
    store_name = st.text_input("اسم المتجر", "متجر ماركات عالمية اصلية")
    store_link = st.text_input("رابط المتجر", "https://legabreil.com/ar")

st.title("⚡ معالج الأوصاف الشامل - كل 3200 منتج")

uploaded = st.file_uploader("ارفع ملف المنتجات (Excel)", type=["xlsx"])

if uploaded:
    raw = uploaded.getvalue()
    wb = openpyxl.load_workbook(io.BytesIO(raw))
    ws = wb.active
    df = pd.read_excel(io.BytesIO(raw), header=1)

    try:
        desc_col = list(df.columns).index("الوصف") + 1
        
        total_products = len(df[df['أسم المنتج'].notna() & (df['أسم المنتج'].astype(str).str.strip() != 'nan')])
        has_desc = df['الوصف'].apply(lambda x: not is_empty(x)).sum()
        no_desc = total_products - has_desc

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='dash-card'><div class='dash-title'>إجمالي المنتجات</div><div class='dash-value'>{total_products:,}</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='dash-card'><div class='dash-title'>لديها وصف</div><div class='dash-value' style='color:#10b981;'>{has_desc:,}</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='dash-card'><div class='dash-title'>بدون وصف</div><div class='dash-value' style='color:#ef4444;'>{no_desc:,}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        mode = st.radio(
            "اختر نطاق المعالجة:",
            ["🔄 كل المنتجات (3200+) - يستبدل الأوصاف الموجودة", "⚡ المنتجات الفارغة فقط"],
            index=0
        )

        if "كل المنتجات" in mode:
            tasks = [
                (i, str(row["أسم المنتج"]).strip())
                for i, row in df.iterrows()
                if str(row["أسم المنتج"]).strip() not in ("nan", "", "None")
            ]
            st.markdown(f"<div class='info-box'>⚠️ سيتم توليد وصف جديد لـ <strong>{len(tasks):,}</strong> منتج وإحلاله محل القديم.</div>", unsafe_allow_html=True)
        else:
            tasks = [
                (i, str(row["أسم المنتج"]).strip())
                for i, row in df.iterrows()
                if is_empty(row["الوصف"]) and str(row["أسم المنتج"]).strip() not in ("nan", "", "None")
            ]
            st.markdown(f"<div class='info-box'>✅ سيتم توليد وصف لـ <strong>{len(tasks):,}</strong> منتج فارغ فقط.</div>", unsafe_allow_html=True)

        # تقدير الوقت
        if len(tasks) > 0 and concurrency > 0:
            est_min = round((len(tasks) / concurrency) * 1.5 / 60, 1)
            st.info(f"⏱️ الوقت المقدر: ~{est_min} دقيقة بـ {concurrency} طلب متزامن")

        if st.button("🚀 بدء المعالجة الشاملة الآن", type="primary", use_container_width=True):
            if not active_keys:
                st.error("❌ أدخل مفتاح API واحداً على الأقل في الشريط الجانبي.")
            elif len(tasks) == 0:
                st.warning("✅ جميع المنتجات لديها أوصاف بالفعل!")
            else:
                st.markdown("### 📊 لوحة المراقبة الحية")
                prog_bar = st.progress(0)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown("<div class='dash-card'><div class='dash-title'>المنجز</div>", unsafe_allow_html=True)
                    comp_st = st.empty()
                    st.markdown("</div>", unsafe_allow_html=True)
                with c2:
                    st.markdown("<div class='dash-card'><div class='dash-title'>نجاح ✅</div>", unsafe_allow_html=True)
                    succ_st = st.empty()
                    st.markdown("</div>", unsafe_allow_html=True)
                with c3:
                    st.markdown("<div class='dash-card'><div class='dash-title'>فشل ❌</div>", unsafe_allow_html=True)
                    fail_st = st.empty()
                    st.markdown("</div>", unsafe_allow_html=True)
                with c4:
                    st.markdown("<div class='dash-card'><div class='dash-title'>الوقت المتبقي</div>", unsafe_allow_html=True)
                    eta_st = st.empty()
                    st.markdown("</div>", unsafe_allow_html=True)

                log_st = st.empty()
                save_st = st.empty()
                dl_st = st.empty()

                ui_components = {
                    'prog': prog_bar, 'comp': comp_st, 'succ': succ_st,
                    'fail': fail_st, 'log': log_st, 'eta': eta_st, 'save': save_st
                }

                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success_count = loop.run_until_complete(
                        run_background_job(
                            tasks, active_keys, model_name, store_name, store_link,
                            concurrency, ui_components, ws, desc_col, save_every, wb,
                            "Salla_Partial_Save.xlsx"
                        )
                    )
                except Exception as e:
                    st.warning(f"توقفت العملية: {e}")
                finally:
                    loop.close()
                    dl_st.markdown(get_download_link(wb, "Salla_All_Products_Completed.xlsx"), unsafe_allow_html=True)
                    st.success(f"🎉 اكتملت المعالجة! نجح: {success_count} من {len(tasks)}")
                    st.balloons()

    except ValueError as e:
        st.error(f"❌ خطأ في الملف: {e}\nتأكد أن الملف يحتوي على عمود 'الوصف' و 'أسم المنتج'")
