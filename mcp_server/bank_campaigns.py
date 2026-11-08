import os
import logging
from mcp.server.mcpserver import MCPServer
from duckduckgo_search import DDGS
from firecrawl import FirecrawlApp
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

mcp = MCPServer("BankCampaignsServer")

@mcp.tool()
def get_bank_campaigns(search_query: str) -> str:
    """
    DuckDuckGo ile en iyi linkleri bulur, Firecrawl ile o linklerin içindeki kampanyaları okur.
    """
    logger.info(f"DDG ile aranıyor: {search_query}")
    
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    if not firecrawl_key:
        return "Firecrawl API anahtarı eksik. Lütfen .env dosyanızı kontrol edin."

    try:
        app = FirecrawlApp(api_key=firecrawl_key)
        
        # 1. DuckDuckGo ile Arama Yap (Yerel siteleri bulmada çok daha başarılı)
        with DDGS() as ddgs:
            # Hem Ziraat hem YapıKredi ihtimaline karşı sonuç sayısını 3 yapıyoruz
            search_results = list(ddgs.text(search_query, region='tr-tr', max_results=3))
            
        if not search_results:
            return "İnternette aktif bir kampanya bulamadım."
        
        scraped_contents = ["--- KAMPANYA SAYFALARI DETAYLI ANALİZİ ---"]
        
        # 2. Bulunan linklerin (Örn: bankkart.com.tr) içine Firecrawl ile gir
        for idx, res in enumerate(search_results, 1):
            title = res.get('title', 'Başlık Yok')
            link = res.get('href', '')
            
            if not link:
                continue
            
            try:
                logger.info(f"Firecrawl siteyi okuyor: {link}")
                
                # Parametre hatası almamak için güvenli scrape
                scrape_result = app.scrape_url(link)
                
                # Pydantic/Dict formatını güvenli şekilde çözümle
                if hasattr(scrape_result, "model_dump"):
                    scrape_dict = scrape_result.model_dump()
                elif hasattr(scrape_result, "dict"):
                    scrape_dict = scrape_result.dict()
                else:
                    scrape_dict = scrape_result
                
                markdown_content = scrape_dict.get('markdown', '')[:4000]
                
                if not markdown_content.strip():
                    markdown_content = res.get('body', 'Site içeriği okunamadı.')
                    
                scraped_contents.append(f"\n### {idx}. Kaynak: {title} ({link})\nİçerik:\n{markdown_content}\n")
                
            except Exception as scrape_err:
                logger.warning(f"Kazıma hatası ({link}): {scrape_err}")
                scraped_contents.append(f"\n### {idx}. Kaynak: {title} ({link})\nÖzet:\n{res.get('body', 'Detay alınamadı.')}\n")
                
        return "\n".join(scraped_contents)
            
    except Exception as e:
        logger.error(f"Arama/Kazıma hatası: {e}", exc_info=True)
        return "Kampanya sayfalarına erişirken bir sorun yaşandı."

if __name__ == "__main__":
    logger.info("Starting FastMCP Bank Campaigns Server with DDG + Firecrawl...")
    mcp.run()