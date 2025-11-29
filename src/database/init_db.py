"""Initialize database tables."""
from sqlalchemy import create_engine
from src.database.models import Base
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def init_database():
    """Create all database tables."""
    try:
        engine = create_engine(settings.database_url)
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    init_database()

