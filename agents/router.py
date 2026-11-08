import os
import logging
from typing import TypedDict, List, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults

# Alt modülleri içe aktar 
from agents.expense_tracker import process_expense
from agents.text_to_sql import analyze_budget

logger = logging.getLogger(__name__)

# 1. Graph State Tanımı
class AgentState(TypedDict):
    messages: List[AnyMessage]
    user_id: str
    intent: str
    final_response: str

# 2. Pydantic Intent (Niyet) Şeması
class IntentClassification(BaseModel):
    intent: Literal["record_expense", "budget_analysis", "campaign_search", "unrelated"] = Field(
        description="Kullanıcı mesajının girdiği kategori."
    )

llm = ChatOpenAI(model="gpt-4o", temperature=0)
structured_router = llm.with_structured_output(IntentClassification)

# 3. Yönlendirici (Router) Düğümü
def classify_intent(state: AgentState) -> dict:
    last_message = state["messages"][-1].content
    logger.info(f"Classifying intent for message: '{last_message}'")
    
    system_prompt = """Sen akıllı bir finans asistanının yönlendirici (router) modülüsün.
    Kullanıcının mesajını analiz et ve sadece şu niyetlerden birini seç:
    - 'record_expense': Para harcama, fiş, fatura ödeme veya gider kaydetme işlemleri.
    - 'budget_analysis': Geçmiş harcamaları sorma, bütçe durumu, kategori bazlı analiz.
    - 'campaign_search': Kredi kartı, banka, taksit veya indirim/kampanya arayışı.
    - 'unrelated': Finans veya harcamalarla tamamen ilgisiz sohbetler."""
    
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=last_message)]
    
    try:
        classification: IntentClassification = structured_router.invoke(messages)
        logger.info(f"Intent classified as: {classification.intent}")
        return {"intent": classification.intent}
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return {"intent": "unrelated"}

# 4. Yönlendirme (Edge) Mantığı
def route_to_agent(state: AgentState) -> str:
    intent = state.get("intent")
    routing_map = {
        "record_expense": "expense_agent",
        "budget_analysis": "sql_agent",
        "campaign_search": "campaign_agent",  # İsmimizi mcp_agent'tan campaign_agent'a güncelledik
        "unrelated": "unrelated_agent"
    }
    return routing_map.get(intent, "unrelated_agent")

# 5. Aksiyon Düğümleri (Action Nodes)
def expense_node(state: AgentState) -> dict:
    last_message = state["messages"][-1].content
    user_id = state.get("user_id", "default_user")
    result = process_expense(last_message, user_id)
    return {"final_response": result["response_message"]}

def sql_node(state: AgentState) -> dict:
    last_message = state["messages"][-1].content
    user_id = state.get("user_id", "default_user")
    result = analyze_budget(last_message, user_id)
    return {"final_response": result["response_message"]}

# YENİ: TAVILY KAMPANYA ARAMA DÜĞÜMÜ
class CampaignSearchExtraction(BaseModel):
    optimized_query: str = Field(..., description="Kullanıcının mesajından banka, kart ve kategoriyi alarak oluşturulan net internet arama sorgusu. Örn: 'Ziraat Bankkart Genç giyim indirim kampanyaları'")

def campaign_node(state: AgentState) -> dict:
    last_message = state["messages"][-1].content
    logger.info(f"Routing to Campaign agent with query: {last_message}")

    try:
        # 1. LLM'den akıllı bir sorgu üretmesini iste (Tavily karmaşık yapıları iyi anlar)
        extractor = llm.with_structured_output(CampaignSearchExtraction)
        extraction = extractor.invoke([
            SystemMessage(content="Kullanıcının mesajından banka ve kategori bilgilerini alarak çok spesifik bir arama motoru sorgusu üret."),
            HumanMessage(content=last_message)
        ])
        search_query = extraction.optimized_query
        logger.info(f"LLM tarafından üretilen akıllı sorgu: {search_query}")

        # 2. Tavily arama aracını kullanarak en iyi 4 sonucu çek (Doğrudan LLM formatında özet döndürür)
        tavily_tool = TavilySearchResults(max_results=4)
        raw_search_results = tavily_tool.invoke({"query": search_query})
        logger.info(f"Tavily sonuçları çekildi.")

        # 3. Bulunan özetleri LLM'e verip düzgün bir Türkçe ile sana aktarmasını sağla
        final_answer = llm.invoke([
            SystemMessage(content="""Sen bir finans asistanısın. Aşağıdaki internet arama sonuçlarını incele. 
            Eğer kampanya detayları (indirim oranı, taksit vb.) sonuçlarda yer alıyorsa bunları net bir şekilde listele. 
            Eğer detaylar eksikse, bulduğun en ilgili resmi kampanya sayfalarının linklerini paylaşarak kullanıcıyı yönlendir.
            Sadece kullanıcının sorduğu bankalar (Örn: Ziraat, Yapı Kredi) ve markalarla ilgili bilgileri ver. İlgisiz haber sitelerini yoksay."""),
            HumanMessage(content=f"Kullanıcı Mesajı: {last_message}\n\nArama Sonuçları:\n{raw_search_results}")
        ]).content

        final_response = final_answer

    except Exception as e:
        logger.error(f"Campaign search node failed: {e}")
        final_response = "Kampanyaları internette ararken geçici bir sorun yaşandı. Lütfen API anahtarlarınızı kontrol edin."

    return {"final_response": final_response}

def unrelated_node(state: AgentState) -> dict:
    return {"final_response": "Ben bir finans asistanıyım. Size harcama takibi, bütçe analizi veya banka kampanyaları konularında yardımcı olabilirim."}

# 6. Grafiği (StateGraph) İnşa Etme
workflow = StateGraph(AgentState)

workflow.add_node("router", classify_intent)
workflow.add_node("expense_agent", expense_node)
workflow.add_node("sql_agent", sql_node)
workflow.add_node("campaign_agent", campaign_node)
workflow.add_node("unrelated_agent", unrelated_node)

workflow.set_entry_point("router")
workflow.add_conditional_edges("router", route_to_agent)

for node in ["expense_agent", "sql_agent", "campaign_agent", "unrelated_agent"]:
    workflow.add_edge(node, END)

app = workflow.compile()