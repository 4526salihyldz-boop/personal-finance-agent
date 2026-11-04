import os
import logging
import psycopg2
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

# 1. LLM'in üreteceği SQL şeması
class SQLQueryOutput(BaseModel):
    query: str = Field(..., description="PostgreSQL için oluşturulan SELECT sorgusu.")
    explanation: str = Field(..., description="Bu sorgunun ne anlama geldiğinin 1-2 cümlelik kısa Türkçe açıklaması.")

# LLM Konfigürasyonu
llm = ChatOpenAI(model="gpt-4o", temperature=0)
structured_llm = llm.with_structured_output(SQLQueryOutput)

# 2. Veritabanı Şeması Bilgisi (Prompt için Context)
SCHEMA_INFO = """
Table: transactions
Columns:
- id (UUID, Primary Key)
- user_id (UUID, Harcamayı yapan kullanıcı)
- amount (DECIMAL, Harcama tutarı TL cinsi)
- category (VARCHAR, Harcama kategorisi. Örn: Market, Ulaşım, Fatura, Yemek, Giyim)
- description (TEXT, Açıklama)
- transaction_date (TIMESTAMP, Harcama tarihi)
"""

# 3. Prompt Tasarımı (Sınırlandırılmış ve Güvenli)
sql_prompt = ChatPromptTemplate.from_messages([
    ("system", f"""Sen kıdemli bir PostgreSQL veri analistisin.
Kullanıcının sorusuna cevap vermek için sadece aşağıdaki şemaya uygun bir SQL sorgusu yaz.
KURALLAR:
1. SADECE 'SELECT' sorguları yazabilirsin. INSERT, UPDATE, DELETE kesinlikle yasak.
2. Sorgun HER ZAMAN 'user_id = {{user_id}}' filtresini içermek zorundadır! (Veri izolasyonu)
3. Tarih filtrelerinde PostgreSQL fonksiyonlarını kullan (örn: EXTRACT(MONTH FROM transaction_date)).
4. Şema Bilgisi:\n{SCHEMA_INFO}"""),
    ("human", "Kullanıcı Sorusu: {user_question}")
])

sql_chain = sql_prompt | structured_llm

def execute_read_only_query(query: str) -> List[Dict]:
    """Supabase PostgreSQL veritabanında güvenli bir şekilde sadece SELECT sorgusu çalıştırır."""
    if not query.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed for security reasons.")
        
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set in environment variables.")

    try:
        # psycopg2 ile doğrudan PostgreSQL bağlantısı
        conn = psycopg2.connect(db_url)
        # Sadece okuma (Read-Only) işlemine zorla
        conn.set_session(readonly=True) 
        
        with conn.cursor() as cur:
            cur.execute(query)
            # Sütun isimlerini ve satırları birleştirip dict listesi döndür
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in cur.fetchall()]
            
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Database query execution failed: {e}")
        raise

def analyze_budget(user_question: str, user_id: str) -> Dict[str, Any]:
    """
    Kullanıcının doğal dil bütçe sorusunu SQL'e çevirir, çalıştırır ve sonucu döndürür.
    """
    try:
        logger.info(f"Translating question to SQL: '{user_question}'")
        
        # user_id'yi prompt'a güvenli bir şekilde enjekte et
        sql_result: SQLQueryOutput = sql_chain.invoke({
            "user_id": f"'{user_id}'", 
            "user_question": user_question
        })
        
        logger.info(f"Generated SQL: {sql_result.query}")
        
        # SQL sorgusunu çalıştır
        query_data = execute_read_only_query(sql_result.query)
        
        # Sonucu daha okunabilir bir metne dönüştürmek için basit bir kural (Gerçekte burası da LLM'e verilebilir)
        if not query_data:
            final_message = "Bu kriterlere uygun bir harcama kaydı bulamadım."
        else:
            # Gelen çiğ veriyi okunabilir bir listeye dönüştürüyoruz
            formatted_results = []
            for row in query_data:
                amount = float(row.get('amount', 0))
                desc = row.get('description', 'Belirtilmedi')
                formatted_results.append(f"- {desc}: {amount} TL")
            
            items_str = "\n".join(formatted_results)
            final_message = f"{sql_result.explanation}\n\n**Bulunan Kayıtlar:**\n{items_str}"
            
        return {
            "status": "success",
            "generated_sql": sql_result.query,
            "data": query_data,
            "response_message": final_message
        }

    except Exception as e:
        logger.error(f"Error in budget analytics: {e}", exc_info=True)
        return {
            "status": "error",
            "response_message": "Bütçe analiziniz yapılırken teknik bir sorun oluştu."
        }