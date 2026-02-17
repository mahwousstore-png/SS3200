"""
description_generator.py
Generates Arabic product descriptions in Lee Gabriel's style using OpenRouter API.
"""

import time
import re
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────────────
# Sample description for few-shot prompting (the real Lee Gabriel style)
# ──────────────────────────────────────────────────────────────────────────────
SAMPLE_DESCRIPTION = """<p>اكتشفوا تجربة فريدة من نوعها مع <strong>تستر عطر مين نيويورك استار دست 75مل</strong>، العطر الذي يجمع بين الأناقة والجرأة في نفحات عصرية تناسب كل الأوقات. هذا الإصدار الخاص من <strong>لي غابريال</strong> يقدم لكم تركيبة غنية تأسر الحواس وتترك انطباعاً لا يُنسى، مع تصميم عملي بدون كرتون يناسب الاستخدام الشخصي أو التجربة قبل الشراء.</p>

<h2 style="background-color: #f9f9f9; border-right: 5px solid #d4af37; padding: 12px 15px; font-family: 'Tajawal'; font-size: 20px; color: #333; margin-top: 25px; border-radius: 4px;">تفاصيل المنتج</h2>
<ul>
  <li><strong>الاسم:</strong> تستر عطر مين نيويورك استار دست 75مل (بدون كرتون)</li>
  <li><strong>السعة:</strong> 75 مل</li>
  <li><strong>نوع المنتج:</strong> عطر رجالي/نسائي (يتميز بطابع عشبي وحيوي)</li>
  <li><strong>الحالة:</strong> تستر بدون علبة كرتون</li>
  <li><strong>الرمز التعريفي (SKU):</strong> 1453582986</li>
  <li><strong>مصمم للعطر:</strong> تركيبة مستوحاة من روح مدينة نيويورك الحيوية</li>
  <li><strong>التغليف:</strong> زجاجة عطر أنيقة وعملية تناسب الاستخدام اليومي</li>
  <li><strong>متوفر عبر:</strong> <a href="#" style="color: #d4af37; font-weight: bold;">لي غابريال</a>، وجهتك المثالية لكل ما يتعلق بالعطور الفاخرة</li>
</ul>

<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 15px; display: inline-block;">رحلة العطر - النفحات والمكونات</h3>
<ul>
  <li><strong>النوتات العليا:</strong> مزيج منعش من الحمضيات كالليمون والبرغموت.</li>
  <li><strong>النوتات الوسطى:</strong> توليفة من الزهور البيضاء مثل الياسمين.</li>
  <li><strong>النوتات الأساسية:</strong> عبق خشبي دافئ من خشب الصندل والباتشولي مع لمسات من العنبر.</li>
</ul>

<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 15px; display: inline-block;">لماذا تختار هذا العطر؟</h3>
<ul>
  <li><strong>تجربة عطرية مميزة:</strong> تركيبة فريدة تعكس روح المدينة العصرية.</li>
  <li><strong>ثبات عالي:</strong> تركيبة متوازنة تضمن بقاء العطر لساعات طويلة.</li>
  <li><strong>تصميم عملي:</strong> زجاجة 75 مل بدون علبة كرتون، مريحة وسهلة الحمل.</li>
  <li><strong>سعر منافس:</strong> خيار مثالي لمن يريد تجربة عطر فاخر بجودة عالية وسعر مناسب.</li>
</ul>

<h3 style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 15px; display: inline-block;">الأسئلة الشائعة</h3>
<ul>
  <li><strong>هل العطر مناسب للاستخدام اليومي؟</strong><br>نعم، العطر متوازن ومناسب لكل الأوقات.</li>
  <li><strong>ما مدى ثبات العطر على الجلد؟</strong><br>يتميز العطر بثبات عالي يدوم لساعات طويلة.</li>
</ul>

<p>مع <strong>تستر عطر مين نيويورك استار دست 75مل</strong> من <a href="#" style="color: #d4af37; font-weight: bold;">لي غابريال</a>، أنت تضمن تجربة عطرية راقية لا تضاهى. اختر التميز، اختر <a href="#" style="color: #d4af37; font-weight: bold;">لي غابريال</a>.</p>"""


def build_system_prompt(tone: str, include_faq: bool, include_notes: bool) -> str:
    """Build the system prompt for the AI model."""
    
    tone_instructions = {
        "فاخر وراقي": "استخدم لغة راقية وفخمة، مع التركيز على الفخامة والأناقة والتميز.",
        "عصري وجذاب": "استخدم لغة عصرية وجذابة، مع التركيز على الحيوية والتجديد.",
        "بسيط ومباشر": "استخدم لغة بسيطة ومباشرة، مع التركيز على المعلومات العملية.",
    }

    sections_instruction = ""
    if include_notes:
        sections_instruction += "\n- تضمين قسم 'رحلة العطر - النفحات والمكونات' مع النوتات العليا والوسطى والأساسية."
    if include_faq:
        sections_instruction += "\n- تضمين قسم 'الأسئلة الشائعة' مع 3-4 أسئلة وأجوبة وثيقة الصلة بالمنتج."

    return f"""أنت كاتب محتوى تجاري متخصص في كتابة وصوف منتجات العطور الفاخرة للمتجر الإلكتروني "لي غابريال".

مهمتك: كتابة وصف HTML احترافي لمنتجات العطور بنفس تنسيق وأسلوب لي غابريال.

## قواعد التنسيق الصارمة:
1. الوصف كله باللغة العربية الفصحى
2. اتجاه النص: RTL (من اليمين لليسار)
3. استخدم نفس هيكل HTML التالي بدقة:
   - فقرة افتتاحية قوية <p>
   - عنوان "تفاصيل المنتج" بهذا الـ style: `style="background-color: #f9f9f9; border-right: 5px solid #d4af37; padding: 12px 15px; font-family: 'Tajawal'; font-size: 20px; color: #333; margin-top: 25px; border-radius: 4px;"`
   - قائمة تفاصيل المنتج <ul>
   {sections_instruction}
   - قسم "لماذا تختار هذا العطر؟" بـ h3 بهذا الـ style: `style="font-size: 18px; color: #d4af37; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 15px; display: inline-block;"`
   - فقرة ختامية تذكر "لي غابريال" مع رابط `style="color: #d4af37; font-weight: bold;"`
4. روابط لي غابريال دائماً: `<a href="#" style="color: #d4af37; font-weight: bold;">لي غابريال</a>`

## أسلوب الكتابة:
{tone_instructions.get(tone, tone_instructions["فاخر وراقي"])}

## مثال على الوصف المطلوب:
{SAMPLE_DESCRIPTION}

## ملاحظات مهمة:
- اكتب معلومات العطر الحقيقية والدقيقة بناءً على اسم المنتج والماركة
- النوتات يجب أن تكون حقيقية لهذا العطر تحديداً
- لا تخترع معلومات غير صحيحة
- أرجع فقط كود HTML بدون أي نص إضافي خارج الكود
"""


def build_user_prompt(product_data: dict) -> str:
    """Build the user prompt for a specific product."""
    
    parts = [f"اكتب وصف HTML كامل للمنتج التالي:\n"]
    
    if product_data.get("name"):
        parts.append(f"**اسم المنتج:** {product_data['name']}")
    if product_data.get("brand"):
        parts.append(f"**الماركة:** {product_data['brand']}")
    if product_data.get("category"):
        parts.append(f"**التصنيف:** {product_data['category']}")
    if product_data.get("sku"):
        parts.append(f"**رمز المنتج (SKU):** {product_data['sku']}")
    if product_data.get("volume"):
        parts.append(f"**الحجم:** {product_data['volume']}")
    if product_data.get("product_type"):
        parts.append(f"**نوع العطر:** {product_data['product_type']}")
    if product_data.get("extra_info"):
        parts.append(f"**معلومات إضافية:** {product_data['extra_info']}")
    
    parts.append("\nاكتب الوصف الآن:")
    return "\n".join(parts)


def generate_description(
    product_data: dict,
    api_key: str,
    model: str = "openai/gpt-4o",
    tone: str = "فاخر وراقي",
    include_faq: bool = True,
    include_notes: bool = True,
) -> str:
    """Generate a single product description."""
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    system_prompt = build_system_prompt(tone, include_faq, include_notes)
    user_prompt = build_user_prompt(product_data)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2500,
        temperature=0.7,
    )
    
    return response.choices[0].message.content.strip()


def generate_batch_descriptions(
    df,
    api_key: str,
    model: str,
    tone: str,
    include_faq: bool,
    include_notes: bool,
    progress_bar=None,
    status_text=None,
    delay: float = 1.5,
):
    """Generate descriptions for a batch of products from a DataFrame."""
    
    import pandas as pd
    
    df = df.copy()
    total = len(df)
    
    # Column name mappings (Salla template)
    col_map = {
        "name": "أسم المنتج",
        "brand": "الماركة",
        "category": "تصنيف المنتج",
        "sku": "رمز المنتج sku",
        "description": "الوصف",
    }
    
    results = []
    
    for idx, (i, row) in enumerate(df.iterrows()):
        progress = (idx + 1) / total
        
        if progress_bar:
            progress_bar.progress(progress)
        if status_text:
            name = str(row.get(col_map["name"], ""))[:40]
            status_text.text(f"⚙️ معالجة ({idx+1}/{total}): {name}...")
        
        product_data = {
            "name": str(row.get(col_map["name"], "") or ""),
            "brand": str(row.get(col_map["brand"], "") or ""),
            "category": str(row.get(col_map["category"], "") or ""),
            "sku": str(row.get(col_map["sku"], "") or ""),
            "volume": "",
            "product_type": "عطر",
            "extra_info": "",
        }
        
        # Try to extract volume from name
        import re
        volume_match = re.search(r"(\d+\s*(?:مل|ml|ML|g|غم))", product_data["name"], re.IGNORECASE)
        if volume_match:
            product_data["volume"] = volume_match.group(1)
        
        try:
            desc = generate_description(
                product_data=product_data,
                api_key=api_key,
                model=model,
                tone=tone,
                include_faq=include_faq,
                include_notes=include_notes,
            )
            df.at[i, col_map["description"]] = desc
            results.append({"index": i, "status": "success"})
        except Exception as e:
            df.at[i, col_map["description"]] = f"<!-- Error: {str(e)} -->"
            results.append({"index": i, "status": "error", "error": str(e)})
        
        if idx < total - 1:
            time.sleep(delay)
    
    if status_text:
        status_text.text(f"✅ اكتملت معالجة {total} منتج!")
    
    return df
