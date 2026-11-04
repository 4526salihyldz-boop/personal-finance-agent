import logging
from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)
mcp = FastMCP("BankCampaignsServer")

@mcp.tool()
def get_bank_campaigns(category: str) -> str:
    """
    Belirtilen kategori için internette canlı arama yaparak herkese açık güncel banka kampanyalarını bulur.
    """
    category_lower = category.lower().strip()
    logger.info(f"İnternette canlı kampanya aranıyor: {category_lower}")
    
    try:
        # DDGS (DuckDuckGo Search) ile ücretsiz, API anahtarsız web araması
        with DDGS() as ddgs:
            search_query = f"güncel {category_lower} markaları indirimleri ve banka kampanyaları"
            
            # Türkiye lokasyonunda en iyi 5 sonucu getir
            results = list(ddgs.text(search_query, region='tr-tr', max_results=5))
            
            if not results:
                return f"İnternette '{category}' kategorisinde aktif bir kampanya bulamadım."
            
            result_lines = [f"--- {category.upper()} KAMPANYALARI (CANLI İNTERNET ARAMASI) ---"]
            for idx, res in enumerate(results, 1):
                # Arama sonuçlarından başlık, özet metin ve linki ayıkla
                title = res.get('title', 'Başlık Bulunamadı')
                body = res.get('body', 'Detay Bulunamadı')
                link = res.get('href', '#')
                
                result_lines.append(f"{idx}. Başlık: {title}\nDetay: {body}\nKaynak Link: {link}\n")
                
            logger.info("Canlı internet araması başarıyla tamamlandı.")
            return "\n".join(result_lines)
            
    except Exception as e:
        logger.error(f"İnternet araması sırasında hata oluştu: {e}", exc_info=True)
        return "Şu anda internetteki kampanya verilerine ulaşamıyorum, ağ bağlantısında bir sorun olabilir."

if __name__ == "__main__":
    logger.info("Starting FastMCP Bank Campaigns Server with Live Web Search...")
    mcp.run()