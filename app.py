import os
import uuid
import logging
import streamlit as st
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Ortam değişkenlerini yükle
load_dotenv()

# Sadece bu modül için loglama ayarı
logger = logging.getLogger(__name__)

# LangGraph orkestrasyonunu içe aktar
# (Eğer hata alırsan agents klasöründe __init__.py dosyasının olduğundan emin ol)
try:
    from agents.router import app as agent_workflow
except ImportError as e:
    logger.error(f"Failed to import LangGraph workflow: {e}")
    agent_workflow = None

# 1. Sayfa Yapılandırması
st.set_page_config(
    page_title="Personal Finance Agent",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Oturum Yönetimi (Session State)
# Kullanıcının sohbet geçmişini ve benzersiz kimliğini oturum boyunca koruyoruz.
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_user_id" not in st.session_state:
    # Veritabanında izolasyonu test etmek için her oturuma geçici bir UUID atanır.
    # Gerçek bir uygulamada burası login (Auth) sisteminden gelir.
    st.session_state.session_user_id = str(uuid.uuid4())

# 3. Kullanıcı Arayüzü (UI) Başlıkları
st.title("💼 Personal Finance Agent")
st.markdown("""
Doğal dilde harcamalarınızı kaydedin, bütçenizi sorgulayın veya güncel kampanyaları keşfedin.
*Örn: "Dün markette 450 TL harcadım" veya "Bu ayki harcamalarım neler?"*
""")

# 4. Sohbet Geçmişini Ekrana Çizme
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Kullanıcı Etkileşimi ve LangGraph Yönlendirmesi
if user_input := st.chat_input("Mesajınızı yazın..."):
    # Kullanıcı mesajını arayüze ve state'e ekle
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # LangGraph'a gönderilecek durum (State) paketi
    state_input = {
        "messages": [HumanMessage(content=user_input)],
        "user_id": st.session_state.session_user_id
    }

    # Asistanın yanıtını oluşturma süreci
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        if agent_workflow is None:
            st.error("Sistem başlatılamadı. Lütfen 'agents' modülünün ve API anahtarlarının doğru yapılandırıldığından emin olun.")
        else:
            with st.spinner("İşleniyor..."):
                try:
                    # Graph'ı tetikle
                    result_state = agent_workflow.invoke(state_input)
                    
                    # Router'ın son düğümünden çıkan 'final_response' değerini al
                    final_answer = result_state.get("final_response", "İşlem tamamlandı, ancak bir yanıt üretilemedi.")
                    
                    response_placeholder.markdown(final_answer)
                    
                    # Yanıtı geçmişe kaydet
                    st.session_state.messages.append({"role": "assistant", "content": final_answer})
                    
                except Exception as e:
                    logger.error(f"Graph execution failed: {e}", exc_info=True)
                    error_msg = "Sistemsel bir hata oluştu. Lütfen tekrar deneyin veya logları kontrol edin."
                    response_placeholder.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})