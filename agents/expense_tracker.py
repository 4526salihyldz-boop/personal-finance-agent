import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from database.supabase_client import db

logger = logging.getLogger(__name__)

# 1. Pydantic Veri Doğrulama Şeması
# LLM'in döneceği verinin tipini ve sınırlarını kesin olarak belirliyoruz.
class ExpenseExtraction(BaseModel):
    amount: float = Field(..., description="Harcama tutarı. Sadece rakam olmalı.")
    category: str = Field(..., description="Harcamanın kategorisi (örn: Market, Ulaşım, Fatura, Yemek, Giyim).")
    description: Optional[str] = Field(None, description="Kullanıcının harcama ile ilgili girdiği ekstra detay.")

# 2. LLM Konfigürasyonu
# Temperature 0: Yaratıcılık istemiyoruz, sadece deterministik veri çıkarımı gerekiyor.
llm = ChatOpenAI(model="gpt-4o", temperature=0)
structured_llm = llm.with_structured_output(ExpenseExtraction)

# 3. Prompt Tasarımı
system_prompt = """Sen bir finansal veri çıkarma asistanısın. 
Kullanıcının mesajından harcama tutarını, kategoriyi ve varsa açıklamayı çıkar.
Eğer kategori net değilse 'Diğer' olarak sınıflandır."""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{user_input}")
])

extraction_chain = prompt_template | structured_llm

def process_expense(user_input: str, user_id: str) -> Dict[str, Any]:
    """
    Kullanıcı girdisini analiz edip harcamayı veritabanına kaydeder.
    
    Args:
        user_input: Kullanıcının girdiği doğal dil metni.
        user_id: İşlemi yapan kullanıcının UUID'si.
        
    Returns:
        State dictionary formatında işlem sonucu ve mesaj.
    """
    try:
        # LLM'den structured data çekimi
        logger.info(f"Extracting expense details from input: '{user_input}'")
        extracted_data: ExpenseExtraction = extraction_chain.invoke({"user_input": user_input})
        
        # Veritabanı kaydı işlemi
        if db is None:
            raise ConnectionError("Database instance is not available.")
            
        record = {
            "user_id": user_id,
            "amount": extracted_data.amount,
            "category": extracted_data.category.capitalize(),
            "description": extracted_data.description or "Belirtilmedi"
        }
        
        # Supabase 'transactions' tablosuna yazma
        response = db.table("transactions").insert(record).execute()
        
        logger.info(f"Expense recorded successfully: {response.data}")
        return {
            "status": "success",
            "extracted_amount": extracted_data.amount,
            "extracted_category": extracted_data.category,
            "response_message": f"Harcamanız kaydedildi: {extracted_data.amount} TL ({extracted_data.category.capitalize()})"
        }

    except ValueError as ve:
        # LLM veriyi beklenen şemada çıkaramazsa (örn: Pydantic validation error)
        logger.error(f"Validation error during extraction: {ve}")
        return {
            "status": "error",
            "response_message": "Harcama tutarını veya kategoriyi tam anlayamadım. Lütfen rakam belirterek tekrar yazar mısınız?"
        }
    except Exception as e:
        logger.error(f"Unexpected error in expense_tracker: {e}", exc_info=True)
        return {
            "status": "error",
            "response_message": "Sistemsel bir hata oluştu, harcama kaydedilemedi."
        }