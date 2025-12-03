"""
Script per resettare le statistiche di consumo token nel database.
Utile per rimuovere dati di test o ripartire da zero.
"""
import logging
import sys
import os

# Aggiungi la directory corrente al path per importare i moduli
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from token_tracker import get_token_tracker

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_token_stats():
    """Resetta la tabella llm_usage"""
    logger.info("🗑️  Avvio reset statistiche token...")
    
    tracker = get_token_tracker()
    
    if not tracker.db_available:
        logger.warning("⚠️  Database non disponibile o non configurato.")
        logger.info("Svuoto solo la cache in-memory...")
        tracker.in_memory_usage = []
        logger.info("✅ Cache in-memory svuotata.")
        return

    try:
        with tracker._get_connection() as conn:
            with conn.cursor() as cur:
                # Conta record prima della cancellazione
                cur.execute("SELECT COUNT(*) FROM llm_usage")
                count = cur.fetchone()[0]
                
                # Tronca la tabella (rimuove tutti i dati e resetta gli ID)
                cur.execute("TRUNCATE TABLE llm_usage RESTART IDENTITY")
            conn.commit()
            
        logger.info(f"✅ Tabella llm_usage svuotata ({count} record rimossi).")
        logger.info("Le statistiche nel dashboard dovrebbero ora essere azzerate.")
        
    except Exception as e:
        logger.error(f"❌ Errore durante il reset delle statistiche: {e}")

if __name__ == "__main__":
    # Chiedi conferma
    print("⚠️  ATTENZIONE: Questo script cancellerà TUTTI i dati storici sul consumo token.")
    confirm = input("Sei sicuro di voler procedere? (s/n): ")
    
    if confirm.lower() in ['s', 'si', 'y', 'yes']:
        reset_token_stats()
    else:
        print("Operazione annullata.")





