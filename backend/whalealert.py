import requests
from datetime import datetime
import json
import logging
import csv
from io import StringIO
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

def get_whale_alerts():
    """
    Recupera i dati whale alerts e formatta gli alert in modo leggibile
    """
    url = "https://whale-alert.io/data.json?alerts=9&prices=BTC&hodl=bitcoin%2CBTC&potential_profit=bitcoin%2CBTC&average_buy_price=bitcoin%2CBTC&realized_profit=bitcoin%2CBTC&volume=bitcoin%2CBTC&news=true"
    
    try:
        # Fai la richiesta GET
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse JSON
        data = response.json()
        
        # Estrai gli alerts
        alerts = data.get('alerts', [])
        
        if not alerts:
            print("Nessun alert trovato.")
            return
        
        print("🐋 WHALE ALERTS - MOVIMENTI CRYPTO SIGNIFICATIVI 🐋\n")
        print("=" * 80)
        
        for alert in alerts:
            # Parse l'alert string (formato: timestamp,emoji,amount,usd_value,description,link)
            parts = alert.split(',', 5)
            
            if len(parts) >= 6:
                timestamp = parts[0]
                emoji = parts[1]
                amount = parts[2].strip('"')
                usd_value = parts[3].strip('"')
                description = parts[4].strip('"')
                link = parts[5]
                
                # Converti timestamp in data leggibile
                try:
                    dt = datetime.fromtimestamp(int(timestamp))
                    formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
                except ValueError:
                    formatted_time = "N/A"
                
                # Stampa alert formattato
                print(f"\n{emoji} ALERT del {formatted_time}")
                print(f"💰 Importo: {amount}")
                print(f"💵 Valore USD: {usd_value}")
                print(f"📝 Descrizione: {description}")
                print(f"🔗 Link: {link}")
                print("-" * 80)
        
    except requests.exceptions.RequestException as e:
        print(f"Errore nella richiesta: {e}")
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing JSON: {e}")
    except Exception as e:
        print(f"Errore generico: {e}")

def format_whale_alerts_to_string():
    """
    Versione che ritorna una stringa formattata invece di stampare
    """
    url = "https://whale-alert.io/data.json?alerts=9&prices=BTC&hodl=bitcoin%2CBTC&potential_profit=bitcoin%2CBTC&average_buy_price=bitcoin%2CBTC&realized_profit=bitcoin%2CBTC&volume=bitcoin%2CBTC&news=true"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        alerts = data.get('alerts', [])
        
        if not alerts:
            return "Nessun alert trovato."
        
        result = "🐋 WHALE ALERTS - MOVIMENTI CRYPTO SIGNIFICATIVI 🐋\n\n"        
        for alert in alerts:
            parts = alert.split(',', 5)
            
            if len(parts) >= 6:
                timestamp = parts[0]
                emoji = parts[1]
                amount = parts[2].strip('"')
                usd_value = parts[3].strip('"')
                description = parts[4].strip('"')
                
                try:
                    dt = datetime.fromtimestamp(int(timestamp))
                    formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
                except ValueError:
                    formatted_time = "N/A"
                
                result += f"\n{emoji} ALERT del {formatted_time}\n"
                result += f"Importo: {amount}\n"
                result += f"Valore USD: {usd_value}\n"
                result += f"Descrizione: {description}\n"
                result += "\n"
        
        return result
        
    except Exception as e:
        return f"Errore: {e}"

def fetch_whale_alerts_from_api(max_alerts: int = 10) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Recupera i whale alerts dall'API pubblica di whale-alert.io e li formatta per il prompt AI.
    Filtra solo gli alert rilevanti per il trading bot (BTC, ETH, SOL, USDT, USDC) o verso/da exchange noti.
    
    Args:
        max_alerts: Numero massimo di alert da includere (default: 10, ma viene limitato a 5 per alert rilevanti)
    
    Returns:
        Tupla (formatted_text, alerts_list):
        - formatted_text: Stringa markdown formattata con gli alert
        - alerts_list: Lista di dizionari con i dati degli alert
    """
    # Asset rilevanti per il trading bot
    RELEVANT_ASSETS = ['BTC', 'ETH', 'SOL', 'USDT', 'USDC']
    
    # Exchange noti (case-insensitive)
    KNOWN_EXCHANGES = [
        'binance', 'okex', 'okx', 'coinbase', 'kraken', 'bitfinex',
        'huobi', 'kucoin', 'bybit', 'gate.io', 'bitmex', 'ftx',
        'gemini', 'crypto.com', 'bitstamp', 'bittrex', 'poloniex'
    ]
    
    def is_relevant_alert(amount: str, description: str) -> bool:
        """
        Verifica se un alert è rilevante per il trading bot.
        
        Args:
            amount: Campo text1 (es. "39,995 #ETH")
            description: Campo text3 (es. "transferred from #OKEX to unknown wallet")
        
        Returns:
            True se l'alert è rilevante, False altrimenti
        """
        # Normalizza i campi per la ricerca (uppercase per asset, lowercase per exchange)
        amount_upper = amount.upper()
        description_upper = description.upper()
        description_lower = description.lower()
        
        # Controlla se amount contiene uno degli asset rilevanti
        for asset in RELEVANT_ASSETS:
            # Cerca il simbolo in vari formati: "#ETH", "ETH", " #ETH", "ETH ", etc.
            if (f'#{asset}' in amount_upper or 
                f' {asset} ' in amount_upper or 
                f' {asset}' in amount_upper or 
                f'{asset} ' in amount_upper or
                amount_upper.endswith(asset) or 
                amount_upper.startswith(asset)):
                return True
        
        # Controlla se description contiene uno degli asset rilevanti
        for asset in RELEVANT_ASSETS:
            if (f'#{asset}' in description_upper or 
                f' {asset} ' in description_upper or 
                f' {asset}' in description_upper or 
                f'{asset} ' in description_upper):
                return True
        
        # Controlla se description menziona exchange noti
        for exchange in KNOWN_EXCHANGES:
            if exchange in description_lower:
                return True
        
        return False
    
    url = "https://whale-alert.io/data.json?alerts=9&prices=BTC&hodl=bitcoin%2CBTC&potential_profit=bitcoin%2CBTC&average_buy_price=bitcoin%2CBTC&realized_profit=bitcoin%2CBTC&volume=bitcoin%2CBTC&news=true"
    
    try:
        logger.info("📡 Recupero whale alerts da whale-alert.io...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        alerts_raw = data.get('alerts', [])
        
        if not alerts_raw:
            logger.warning("⚠️ Nessun alert trovato nella risposta")
            return "Whale alert non disponibili", []
        
        # Parsa gli alert CSV
        alerts_parsed = []
        for alert_str in alerts_raw:
            if not alert_str or not isinstance(alert_str, str):
                continue
            
            try:
                # Usa csv.reader per gestire correttamente le virgole nei numeri
                # Il formato è: timestamp,emoji,text1,text2,text3,link
                reader = csv.reader(StringIO(alert_str))
                parts = next(reader)
                
                if len(parts) >= 6:
                    timestamp = parts[0].strip()
                    emoji = parts[1].strip()
                    amount = parts[2].strip().strip('"')  # quantità trasferita (text1)
                    usd_value = parts[3].strip().strip('"')  # valore USD (text2)
                    description = parts[4].strip().strip('"')  # descrizione (text3)
                    link = parts[5].strip()  # link alla transazione
                    
                    # Filtra solo alert rilevanti
                    if not is_relevant_alert(amount, description):
                        logger.debug(f"⚠️ Alert filtrato (non rilevante): {amount[:50]}...")
                        continue
                    
                    # Estrai valore USD numerico per ordinamento (rimuovi $ e virgole)
                    try:
                        usd_numeric = float(usd_value.replace('$', '').replace(',', ''))
                    except (ValueError, AttributeError):
                        usd_numeric = 0.0
                    
                    alerts_parsed.append({
                        'timestamp': timestamp,
                        'emoji': emoji,
                        'amount': amount,
                        'usd_value': usd_value,
                        'description': description,
                        'link': link,
                        'usd_numeric': usd_numeric
                    })
                else:
                    logger.debug(f"⚠️ Alert malformato (campi insufficienti): {alert_str[:50]}...")
                    
            except Exception as e:
                logger.debug(f"⚠️ Errore parsing alert: {e}, alert: {alert_str[:50]}...")
                continue
        
        if not alerts_parsed:
            logger.warning("⚠️ Nessun alert rilevante trovato dopo il filtro")
            return "Nessun whale alert rilevante nelle ultime ore.", []
        
        # Ordina per valore USD decrescente (più grandi prima)
        alerts_parsed.sort(key=lambda x: x['usd_numeric'], reverse=True)
        
        # Limita a massimo 5 alert rilevanti (come specificato)
        alerts_parsed = alerts_parsed[:5]
        
        # Formatta in markdown (senza emoji per risparmiare token)
        formatted_lines = []
        alerts_list = []
        
        for alert in alerts_parsed:
            # Normalizza formato USD: assicura che abbia il simbolo $
            usd_value_formatted = alert['usd_value']
            if usd_value_formatted and not usd_value_formatted.startswith('$'):
                # Se contiene "USD" alla fine, sostituisci con $ all'inizio
                if 'USD' in usd_value_formatted:
                    usd_value_formatted = '$' + usd_value_formatted.replace(' USD', '').replace('USD', '').strip()
                else:
                    usd_value_formatted = '$' + usd_value_formatted.strip()
            
            # Formato senza emoji: 39,995 ETH ($119,668,458) transferred from unknown wallet to unknown wallet
            # Link: https://whale-alert.io/transaction/ethereum/0x... (verificabile su Etherscan/Solscan/TronScan/BscScan)
            formatted_line = f"{alert['amount']} ({usd_value_formatted}) {alert['description']}"
            formatted_lines.append(formatted_line)
            
            # Estrai blockchain dal link per aggiungere nota verificabilità
            blockchain = "blockchain"
            if "/ethereum/" in alert['link']:
                blockchain = "Ethereum (Etherscan)"
            elif "/solana/" in alert['link']:
                blockchain = "Solana (Solscan)"
            elif "/tron/" in alert['link']:
                blockchain = "Tron (TronScan)"
            elif "/bsc/" in alert['link'] or "/binance/" in alert['link']:
                blockchain = "BSC (BscScan)"
            
            formatted_lines.append(f"Link: {alert['link']} (verificabile su {blockchain})")
            formatted_lines.append("")  # Linea vuota tra alert
            
            # Aggiungi alla lista JSON
            alerts_list.append({
                'amount': alert['amount'],
                'usd_value': alert['usd_value'],
                'description': alert['description'],
                'link': alert['link'],
                'timestamp': alert['timestamp']
            })
        
        formatted_text = "\n".join(formatted_lines).strip()
        
        logger.info(f"✅ Whale alerts recuperati: {len(alerts_parsed)} alert rilevanti (filtrati per asset: {', '.join(RELEVANT_ASSETS)})")
        return formatted_text, alerts_list
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ Errore HTTP nel recupero whale alerts: {e}")
        return "Whale alert non disponibili", []
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ Errore parsing JSON whale alerts: {e}")
        return "Whale alert non disponibili", []
    except Exception as e:
        logger.warning(f"⚠️ Errore generico nel recupero whale alerts: {e}", exc_info=True)
        return "Whale alert non disponibili", []


# Esempio di utilizzo
if __name__ == "__main__":
    # Versione che stampa direttamente
    get_whale_alerts()
    
    # O se preferisci ottenere una stringa
    # formatted_alerts = format_whale_alerts_to_string()
    # print(formatted_alerts)
    
    # Test nuova funzione
    logging.basicConfig(level=logging.INFO)
    whale_txt, whale_data = fetch_whale_alerts_from_api()
    print("\n" + "="*80)
    print("TEST fetch_whale_alerts_from_api():")
    print("="*80)
    print(whale_txt)
    print("\n" + "="*80)
    print(f"Alert count: {len(whale_data)}")
    if whale_data:
        print(f"First alert: {json.dumps(whale_data[0], indent=2)}")