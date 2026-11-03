import logging
import asyncio
from mcp.server.fastmcp import FastMCP

# Loglama yapılandırması
logger = logging.getLogger(__name__)

# FastMCP sunucusunu başlat
mcp = FastMCP("BankCampaignsServer")

# Geçici mock veritabanı (Gerçek senaryoda bu veri banka API'lerinden veya bir Redis cache'ten gelir)
MOCK_CAMPAIGNS = {
    "market": [
        {"bank": "Garanti BBVA", "detail": "Bonus ile market alışverişlerinde 500 TL'ye varan bonus.", "min_spend": 1000},
        {"bank": "İş Bankası", "detail": "Maximum Kart ile 3. market alışverişinize 100 MaxiPuan.", "min_spend": 500}
    ],
    "elektronik": [
        {"bank": "Yapı Kredi", "detail": "Worldcard ile Vatan Bilgisayar'da peşin fiyatına 6 taksit.", "min_spend": 5000}
    ],
    "giyim": [
        {"bank": "Akbank", "detail": "Axess ile giyim sektöründe %10 chip-para iadesi.", "min_spend": 0}
    ]
}

@mcp.tool()
async def get_bank_campaigns(category: str) -> str:
    """
    Belirtilen harcama kategorisi için güncel banka ve kredi kartı kampanyalarını getirir.
    
    Args:
        category: Harcama yapılacak kategori (örn: 'market', 'elektronik', 'giyim').
    """
    logger.info(f"Campaign search requested for category: {category}")
    category_lower = category.lower().strip()
    
    try:
        # Gerçek bir API isteğini simüle etmek için asenkron gecikme
        await asyncio.sleep(0.5)
        
        campaigns = MOCK_CAMPAIGNS.get(category_lower)
        
        if not campaigns:
            logger.warning(f"No campaigns found for category: {category_lower}")
            return f"Şu anda '{category}' kategorisinde aktif bir kampanya bulunamadı."
        
        # Yanıtı LLM'in kolayca anlayıp yorumlayabileceği yapılandırılmış bir metne çeviriyoruz
        result_lines = [f"--- {category.upper()} KATEGORİSİ KAMPANYALARI ---"]
        for idx, camp in enumerate(campaigns, 1):
            result_lines.append(
                f"{idx}. Banka: {camp['bank']} | Min. Harcama: {camp['min_spend']} TL | Detay: {camp['detail']}"
            )
            
        logger.info(f"Successfully retrieved {len(campaigns)} campaigns for {category_lower}")
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error fetching bank campaigns: {e}", exc_info=True)
        return "Kampanya verilerine ulaşırken geçici bir bağlantı sorunu yaşandı."

if __name__ == "__main__":
    # Sunucuyu standart IO (veya SSE) üzerinden ayağa kaldır
    logger.info("Starting FastMCP Bank Campaigns Server...")
    mcp.run()