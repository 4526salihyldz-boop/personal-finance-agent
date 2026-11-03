import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

#ortam değiskenlerini .env dosyasından alıyoruz
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SupabaseManager:
    """
    Singleton pattern to manage Supabase database connection.
    Ensures only a single client instance is created during the application lifecycle.
    """
    _instance = None
    _client: Client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            logger.error("Supabase credentials missing. Check your .env file.")
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set.")

        try:
            self._client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to connect to Supabase: {e}")
            raise

    @property
    def client(self) -> Client:
        return self._client

# Expose a ready-to-use client instance
try:
    db = SupabaseManager().client
except Exception as e:
    logger.error("Database connection could not be established. Ensure credentials are valid.")
    db = None