import json
import time
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any

import eth_account
from eth_account.signers.local import LocalAccount

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.utils.error import ClientError
from hyperliquid_utils import init_info_with_retry


class HyperLiquidTrader:
    def __init__(
        self,
        secret_key: str,
        account_address: str,
        master_account_address: str = None,
        testnet: bool = True,
        skip_ws: bool = True,
    ):
        self.secret_key = secret_key
        self.account_address = account_address  # API wallet per Exchange (trading)
        self.master_account_address = master_account_address or account_address  # Master Account per Info (lettura)

        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self.base_url = base_url

        # crea account signer
        account: LocalAccount = eth_account.Account.from_key(secret_key)

        # Inizializza Info con retry logic per gestire rate limiting
        self.info = init_info_with_retry(base_url, skip_ws=skip_ws)
        # Exchange usa account_address (API wallet) per le operazioni di trading
        self.exchange = Exchange(account, base_url, account_address=account_address)

        # cache meta per tick-size e min-size (anche questo può ricevere 429, ma è meno critico)
        try:
            self.meta = self.info.meta()
        except ClientError as e:
            error_args = e.args[0] if e.args else None
            if isinstance(error_args, tuple) and len(error_args) > 0 and error_args[0] == 429:
                print("⚠️ Rate limit (429) su meta(), continuo senza cache...")
                self.meta = None  # Continua senza cache, verrà ricaricato quando necessario
            else:
                raise

    def _to_hl_size(self, size_decimal: Decimal) -> str:
        # HL accetta max 8 decimali
        size_clamped = size_decimal.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        return format(size_clamped, "f")   # HL vuole stringa decimale perfetta

    # ----------------------------------------------------------------------
    #                            VALIDAZIONE INPUT
    # ----------------------------------------------------------------------
    def _validate_order_input(self, order_json: Dict[str, Any]):
        required_fields = [
            "operation",
            "symbol",
            "direction",
            "target_portion_of_balance",
            "leverage",
            "reason",
        ]

        for f in required_fields:
            if f not in order_json:
                raise ValueError(f"Missing required field: {f}")

        if order_json["operation"] not in ("open", "close", "hold"):
            raise ValueError("operation must be 'open', 'close', or 'hold'")

        if order_json["direction"] not in ("long", "short"):
            raise ValueError("direction must be 'long' or 'short'")

        try:
            float(order_json["target_portion_of_balance"])
        except:
            raise ValueError("target_portion_of_balance must be a number")

    # ----------------------------------------------------------------------
    #                           MIN SIZE / TICK SIZE
    # ----------------------------------------------------------------------
    def _get_min_tick_for_symbol(self, symbol: str) -> Decimal:
        """
        Hyperliquid definisce per ogni asset un tick size.
        Lo leggiamo da meta().
        """
        for perp in self.meta["universe"]:
            if perp["name"] == symbol:
                return Decimal(str(perp["szDecimals"]))
        return Decimal("0.00000001")  # fallback a 1e-8

    def _round_size(self, size: Decimal, decimals: int) -> float:
        """
        Hyperliquid accetta massimo 8 decimali.
        Inoltre dobbiamo rispettare il tick size.
        """
        # prima clamp a 8 decimali
        size = size.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

        # poi count of decimals per il tick
        fmt = f"{{0:.{decimals}f}}"
        return float(fmt.format(size))

    # ----------------------------------------------------------------------
    #                        GESTIONE LEVA
    # ----------------------------------------------------------------------
    def get_current_leverage(self, symbol: str) -> Dict[str, Any]:
        """Ottieni info sulla leva corrente per un simbolo"""
        try:
            user_state = self.info.user_state(self.master_account_address)
            
            # Cerca nelle posizioni aperte
            for position in user_state.get('assetPositions', []):
                pos = position.get('position', {})
                coin = pos.get('coin', '')
                if coin == symbol:
                    leverage_info = pos.get('leverage', {})
                    return {
                        'value': leverage_info.get('value', 0),
                        'type': leverage_info.get('type', 'unknown'),
                        'coin': coin
                    }
            
            # Se non c'è posizione aperta, controlla cross leverage default
            cross_leverage = user_state.get('crossLeverage', 20)
            return {
                'value': cross_leverage,
                'type': 'cross',
                'coin': symbol,
                'note': 'No open position, showing account default'
            }
            
        except Exception as e:
            print(f"Errore ottenendo leva corrente: {e}")
            return {'value': 20, 'type': 'unknown', 'error': str(e)}

    def set_leverage_for_symbol(self, symbol: str, leverage: int, is_cross: bool = True) -> Dict[str, Any]:
        """Imposta la leva per un simbolo specifico usando il metodo corretto"""
        try:
            print(f"🔧 Impostando leva {leverage}x per {symbol} ({'cross' if is_cross else 'isolated'} margin)")
            
            # Usa il metodo update_leverage con i parametri corretti
            result = self.exchange.update_leverage(
                leverage=leverage,      # int
                name=symbol,           # str - nome del simbolo come "BTC"
                is_cross=is_cross      # bool
            )
            
            if result.get('status') == 'ok':
                print(f"✅ Leva impostata con successo a {leverage}x per {symbol}")
            else:
                print(f"⚠️ Risposta dall'exchange: {result}")
                
            return result
            
        except Exception as e:
            print(f"❌ Errore impostando leva per {symbol}: {e}")
            return {"status": "error", "error": str(e)}

    # ----------------------------------------------------------------------
    #                        ESECUZIONE SEGNALE AI
    # ----------------------------------------------------------------------
    def execute_signal(self, order_json: Dict[str, Any]) -> Dict[str, Any]:
        from decimal import Decimal, ROUND_DOWN

        self._validate_order_input(order_json)

        op = order_json["operation"]
        symbol = order_json["symbol"]
        direction = order_json["direction"]
        portion = Decimal(str(order_json["target_portion_of_balance"]))
        leverage = int(order_json.get("leverage", 1))

        if op == "hold":
            print(f"[HyperLiquidTrader] HOLD — nessuna azione per {symbol}.")
            return {"status": "hold", "message": "No action taken."}

        if op == "close":
            print(f"[HyperLiquidTrader] Market CLOSE per {symbol}")
            
            # Verifica se esiste una posizione aperta e ottieni il simbolo esatto
            try:
                account_status = self.get_account_status()
                open_positions = account_status.get("open_positions", [])
                
                # Cerca la posizione - può essere con simbolo esatto o simile
                matching_position = None
                for pos in open_positions:
                    pos_symbol = pos.get("symbol", "")
                    # Match esatto o parziale (es. "BTC" matcha "BTC" o contiene "BTC")
                    if pos_symbol == symbol or symbol in pos_symbol or pos_symbol in symbol:
                        matching_position = pos
                        break
                
                if not matching_position:
                    return {
                        "status": "skipped",
                        "message": f"Nessuna posizione aperta per {symbol} da chiudere"
                    }
                
                # Usa il simbolo esatto dalla posizione
                exact_symbol = matching_position.get("symbol", symbol)
                position_size = matching_position.get("size", 0)
                position_side = matching_position.get("side", "long")
                
                print(f"[HyperLiquidTrader] Chiusura posizione: {exact_symbol}, size: {position_size}, side: {position_side}")
                
            except Exception as e:
                # Se non riusciamo a verificare, procediamo comunque con market_close usando il simbolo originale
                print(f"⚠️ Impossibile verificare posizione per {symbol}: {e}")
                exact_symbol = symbol
            
            # Prova a chiudere con market_close
            print(f"[HyperLiquidTrader] Tentativo market_close per {exact_symbol}...")
            result = self.exchange.market_close(exact_symbol)
            
            # Log dettagliato del risultato
            print(f"[HyperLiquidTrader] market_close result: {result}")
            print(f"[HyperLiquidTrader] result type: {type(result)}")
            
            # Se market_close ritorna None, prova metodo alternativo
            if result is None:
                print(f"⚠️ market_close ritornato None per {exact_symbol}, provo metodo alternativo...")
                
                try:
                    # Metodo alternativo: chiudi aprendo una posizione opposta della stessa dimensione
                    account_status_retry = self.get_account_status()
                    open_positions_retry = account_status_retry.get("open_positions", [])
                    
                    for pos in open_positions_retry:
                        if pos.get("symbol") == exact_symbol:
                            pos_size = pos.get("size", 0)
                            pos_side = pos.get("side", "long")
                            
                            # Apri posizione opposta per chiudere
                            is_buy = (pos_side == "short")  # Se era short, compra per chiudere
                            
                            # market_open richiede un float, non una stringa
                            size_to_close = float(pos_size)
                            
                            print(f"[HyperLiquidTrader] Tentativo chiusura alternativa: {'BUY' if is_buy else 'SELL'} {size_to_close} {exact_symbol}")
                            
                            alt_result = self.exchange.market_open(
                                exact_symbol,
                                is_buy,
                                size_to_close,
                                None,  # SL
                                0.01   # Slippage
                            )
                            
                            print(f"[HyperLiquidTrader] Metodo alternativo result: {alt_result}")
                            
                            if alt_result and isinstance(alt_result, dict) and alt_result.get("status") != "err":
                                return {
                                    "status": "ok",
                                    "message": f"Posizione {exact_symbol} chiusa con metodo alternativo",
                                    "method": "alternative"
                                }
                            break
                except Exception as e:
                    print(f"❌ Errore metodo alternativo: {e}")
                
                # Se anche il metodo alternativo fallisce
                return {
                    "status": "error",
                    "message": f"market_close returned None per {exact_symbol} - posizione ancora aperta. Verifica manualmente.",
                    "symbol_used": exact_symbol
                }
            
            # Se result è un dizionario con status "err", è un errore
            if isinstance(result, dict) and result.get("status") == "err":
                error_msg = result.get("response", {}).get("data", "Errore sconosciuto")
                return {
                    "status": "error",
                    "message": f"Errore chiusura {exact_symbol}: {error_msg}",
                    "symbol_used": exact_symbol
                }
            
            return result

        # OPEN --------------------------------------------------------
        # Prima di aprire la posizione, imposta la leva desiderata
        leverage_result = self.set_leverage_for_symbol(
            symbol=symbol,
            leverage=leverage,
            is_cross=True  # Puoi cambiare in False per isolated margin
        )
        
        if leverage_result.get('status') != 'ok':
            print(f"⚠️ Attenzione: impostazione leva potrebbe aver avuto problemi: {leverage_result}")
        
        # Piccola pausa per assicurarsi che la leva sia applicata
        import time
        time.sleep(0.5)
        
        # Verifica la leva attuale dopo l'aggiornamento
        current_leverage_info = self.get_current_leverage(symbol)
        print(f"📊 Leva attuale per {symbol}: {current_leverage_info}")

        # Ora procedi con l'apertura della posizione
        user = self.info.user_state(self.master_account_address)
        balance_usd = Decimal(str(user["marginSummary"]["accountValue"]))

        if balance_usd <= 0:
            raise RuntimeError("Balance account = 0")

        notional = balance_usd * portion * Decimal(str(leverage))

        mids = self.info.all_mids()
        if symbol not in mids:
            raise RuntimeError(f"Symbol {symbol} non presente su HL")

        mark_px = Decimal(str(mids[symbol]))
        raw_size = notional / mark_px

        # Ottieni info sul simbolo dalla meta
        symbol_info = None
        for perp in self.meta["universe"]:
            if perp["name"] == symbol:
                symbol_info = perp
                break
        
        if not symbol_info:
            raise RuntimeError(f"Symbol {symbol} non trovato nella meta universe")

        # IMPORTANTE: Ottieni il minimum order size (non szDecimals!)
        min_size = Decimal(str(symbol_info.get("minSz", "0.001")))
        sz_decimals = int(symbol_info.get("szDecimals", 8))
        max_leverage = symbol_info.get("maxLeverage", 100)

        # Verifica che la leva richiesta non superi il massimo
        if leverage > max_leverage:
            print(f"⚠️ Leva richiesta ({leverage}) supera il massimo per {symbol} ({max_leverage})")

        # Arrotonda secondo i decimali permessi
        quantizer = Decimal(10) ** -sz_decimals
        size_decimal = raw_size.quantize(quantizer, rounding=ROUND_DOWN)

        # Verifica che sia sopra il minimo
        if size_decimal < min_size:
            print(f"⚠️ Size calcolata ({size_decimal}) < minima richiesta ({min_size})")
            print(f"   Raw size: {raw_size}, Balance: {balance_usd}, Portion: {portion}, Leverage: {leverage}")
            print(f"   Notional: {notional}, Mark price: {mark_px}")
            
            # Usa direttamente il minimum size
            size_decimal = min_size

        # Converti a float per l'API
        size_float = float(size_decimal)

        is_buy = (direction == "long")

        print(
            f"\n[HyperLiquidTrader] Market {'BUY' if is_buy else 'SELL'} "
            f"{size_float} {symbol}\n"
            f"  💰 Prezzo: ${mark_px}\n"
            f"  📊 Notional: ${notional:.2f}\n"
            f"  🎯 Leva target: {leverage}x\n"
        )

        res = self.exchange.market_open(
            symbol,
            is_buy,
            size_float,
            None,
            0.01
        )

        # Assicurati che res sia sempre un dizionario
        if res is None:
            return {"status": "error", "message": "market_open returned None"}
        
        return res

    # ----------------------------------------------------------------------
    #                           STATO ACCOUNT
    # ----------------------------------------------------------------------
    def get_account_status(self) -> Dict[str, Any]:
        """
        Ottiene lo stato dell'account Hyperliquid.
        Include sia Perps che Spot account.
        
        Returns:
            Dict con balance_usd (total equity), perps_balance, spot_balance e open_positions
        """
        import time
        from hyperliquid.utils.error import ClientError

        max_retries = 5
        retry_delay = 3  # seconds

        data = {}
        
        # Retry logic per user_state (Perps)
        for attempt in range(max_retries):
            try:
                # Usa master_account_address per le chiamate di lettura (Info)
                # Il master account è quello che contiene i fondi
                data = self.info.user_state(self.master_account_address)
                break # Success
            except ClientError as e:
                error_args = e.args[0] if e.args else None
                # Check for 429 Too Many Requests
                if isinstance(error_args, tuple) and len(error_args) > 0 and error_args[0] == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 3, 6, 12, 24, 48s
                        print(f"⚠️ Rate limit (429) su user_state, retry in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                print(f"❌ Errore recupero user_state: {e}")
                raise
            except Exception as e:
                print(f"❌ Errore recupero user_state: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise
        
        # Estrai balance da marginSummary (Perps Account)
        margin_summary = data.get("marginSummary", {})
        perps_balance = float(margin_summary.get("accountValue", "0.0"))
        
        # Estrai balance da crossMarginSummary (include Spot + Perps)
        cross_margin_summary = data.get("crossMarginSummary", {})
        total_equity = float(cross_margin_summary.get("accountValue", "0.0"))
        
        # Prova a recuperare saldi Spot direttamente
        spot_balance = 0.0
        try:
            spot_state = self.info.spot_user_state(self.master_account_address)
            if isinstance(spot_state, dict) and "balances" in spot_state:
                # Calcola il totale dei saldi Spot
                for balance_item in spot_state.get("balances", []):
                    if isinstance(balance_item, dict):
                        # Cerca il valore in USD o USDC
                        total = balance_item.get("total", "0")
                        coin = balance_item.get("coin", "")
                        if coin == "USDC" or coin == "USD":
                            spot_balance += float(total)
        except Exception as e:
            # Se spot_user_state fallisce, continua senza Spot balance
            pass
        
        # Se total_equity è 0, prova a sommare Perps + Spot
        if total_equity == 0.0:
            total_equity = perps_balance + spot_balance
        
        # Se ancora 0, usa perps_balance come fallback
        if total_equity == 0.0 and perps_balance > 0.0:
            total_equity = perps_balance
        
        # Workaround per testnet: se tutto è 0 ma withdrawable > 0, usa quello
        withdrawable = float(data.get("withdrawable", "0.0"))
        if total_equity == 0.0 and withdrawable > 0.0:
            total_equity = withdrawable
            print(f"💡 Usando withdrawable come fallback: ${withdrawable}")
        
        # Usa total_equity come balance principale
        balance = total_equity
        
        # Log per debug se balance è zero
        if balance == 0.0:
            print(f"⚠️ ATTENZIONE: Saldo zero per Master Account {self.master_account_address}")
            print(f"   Base URL: {self.base_url}")
            print(f"   API Wallet: {self.account_address}")
            print(f"   Master Account: {self.master_account_address}")
            print(f"   Margin Summary (Perps): {margin_summary}")
            print(f"   Cross Margin Summary (Total): {cross_margin_summary}")
            print(f"   Spot Balance (da spot_user_state): ${spot_balance}")
            print(f"   Withdrawable: {data.get('withdrawable', '0.0')}")
            print(f"   💡 NOTA: Verifica che MASTER_ACCOUNT_ADDRESS nel .env sia corretto")
            print(f"      e che il Master Account abbia fondi su Perps.")
            if "testnet" in self.base_url:
                print(f"      Verifica sul sito: https://app.hyperliquid-testnet.xyz/portfolio")

        mids = self.info.all_mids()
        positions = []

        # Gestisci il formato corretto dei dati
        asset_positions = data.get("assetPositions", [])
        
        # DEBUG LOGGING
        print(f"[DEBUG] Raw assetPositions: {asset_positions}")
        
        for p in asset_positions:
            # Estrai la posizione dal formato corretto
            if isinstance(p, dict) and "position" in p:
                pos = p["position"]
                coin = pos.get("coin", "")
            else:
                # Se il formato è diverso, prova ad adattarti
                pos = p
                coin = p.get("coin", p.get("symbol", ""))
                
            if not pos or not coin:
                continue
                
            size = float(pos.get("szi", 0))
            if size == 0:
                continue

            entry = float(pos.get("entryPx", 0))
            mark = float(mids.get(coin, entry))

            # Calcola P&L
            pnl = (mark - entry) * size
            
            # Estrai info sulla leva
            leverage_info = pos.get("leverage", {})
            leverage_value = leverage_info.get("value", "N/A")
            leverage_type = leverage_info.get("type", "unknown")

            positions.append({
                "symbol": coin,
                "side": "long" if size > 0 else "short",
                "size": abs(size),
                "entry_price": entry,
                "mark_price": mark,
                "pnl_usd": round(pnl, 4),
                "leverage": f"{leverage_value}x ({leverage_type})"
            })

        return {
            "balance_usd": balance,  # Total Equity (Perps + Spot)
            "perps_balance_usd": perps_balance,  # Solo Perps Account
            "spot_balance_usd": spot_balance,  # Solo Spot Account (calcolato)
            "open_positions": positions,
        }
    
    # ----------------------------------------------------------------------
    #                    RISK MANAGEMENT METHODS
    # ----------------------------------------------------------------------
    def execute_signal_with_risk(
        self,
        order_json: Dict[str, Any],
        risk_manager: 'RiskManager',
        balance_usd: float
    ) -> Dict[str, Any]:
        """
        Esegue un segnale con risk management integrato.

        Args:
            order_json: Decisione dal trading agent
            risk_manager: Istanza del RiskManager
            balance_usd: Balance corrente

        Returns:
            Dict con risultato dell'operazione
        """
        from risk_manager import RiskManager  # Import locale per evitare circular

        op = order_json.get("operation", "hold")
        symbol = order_json.get("symbol", "BTC")
        direction = order_json.get("direction", "long")

        # HOLD - nessuna azione
        if op == "hold":
            return {"status": "hold", "message": "Nessuna azione"}

        # CLOSE - chiudi posizione
        if op == "close":
            # Verifica se esiste una posizione aperta e ottieni il simbolo esatto
            try:
                account_status = self.get_account_status()
                open_positions = account_status.get("open_positions", [])
                
                # Cerca la posizione - può essere con simbolo esatto o simile
                matching_position = None
                for pos in open_positions:
                    pos_symbol = pos.get("symbol", "")
                    # Match esatto o parziale (es. "BTC" matcha "BTC" o contiene "BTC")
                    if pos_symbol == symbol or symbol in pos_symbol or pos_symbol in symbol:
                        matching_position = pos
                        break
                
                if not matching_position:
                    # Rimuovi comunque dal tracking se non esiste più
                    risk_manager.remove_position(symbol)
                    return {
                        "status": "skipped",
                        "message": f"Nessuna posizione aperta per {symbol} da chiudere"
                    }
                
                # Usa il simbolo esatto dalla posizione
                exact_symbol = matching_position.get("symbol", symbol)
                position_size = matching_position.get("size", 0)
                position_side = matching_position.get("side", "long")
                
                print(f"[HyperLiquidTrader] Chiusura posizione: {exact_symbol}, size: {position_size}, side: {position_side}")
                
            except Exception as e:
                # Se non riusciamo a verificare, procediamo comunque con market_close usando il simbolo originale
                print(f"⚠️ Impossibile verificare posizione per {symbol}: {e}")
                exact_symbol = symbol
            
            # Prova a chiudere con market_close
            print(f"[HyperLiquidTrader] Tentativo market_close per {exact_symbol}...")
            result = self.exchange.market_close(exact_symbol)
            
            # Log dettagliato del risultato
            print(f"[HyperLiquidTrader] market_close result: {result}")
            print(f"[HyperLiquidTrader] result type: {type(result)}")
            
            # Se market_close ritorna None, prova metodo alternativo
            if result is None:
                print(f"⚠️ market_close ritornato None per {exact_symbol}, provo metodo alternativo...")
                
                try:
                    # Metodo alternativo: chiudi aprendo una posizione opposta della stessa dimensione
                    # Questo è un workaround se market_close non funziona
                    account_status_retry = self.get_account_status()
                    open_positions_retry = account_status_retry.get("open_positions", [])
                    
                    for pos in open_positions_retry:
                        if pos.get("symbol") == exact_symbol:
                            pos_size = pos.get("size", 0)
                            pos_side = pos.get("side", "long")
                            
                            # Apri posizione opposta per chiudere
                            is_buy = (pos_side == "short")  # Se era short, compra per chiudere
                            
                            # market_open richiede un float, non una stringa
                            size_to_close = float(pos_size)
                            
                            print(f"[HyperLiquidTrader] Tentativo chiusura alternativa: {'BUY' if is_buy else 'SELL'} {size_to_close} {exact_symbol}")
                            
                            alt_result = self.exchange.market_open(
                                exact_symbol,
                                is_buy,
                                size_to_close,
                                None,  # SL
                                0.01   # Slippage
                            )
                            
                            print(f"[HyperLiquidTrader] Metodo alternativo result: {alt_result}")
                            
                            if alt_result and isinstance(alt_result, dict) and alt_result.get("status") != "err":
                                # Rimuovi dal tracking solo se la chiusura alternativa ha funzionato
                                risk_manager.remove_position(symbol)
                                return {
                                    "status": "ok",
                                    "message": f"Posizione {exact_symbol} chiusa con metodo alternativo",
                                    "method": "alternative"
                                }
                            break
                except Exception as e:
                    print(f"❌ Errore metodo alternativo: {e}")
                
                # Se anche il metodo alternativo fallisce, NON rimuovere dal tracking
                return {
                    "status": "error",
                    "message": f"market_close returned None per {exact_symbol} - posizione ancora aperta. Verifica manualmente.",
                    "symbol_used": exact_symbol
                }
            
            # Se result è un dizionario con status "err", è un errore
            if isinstance(result, dict) and result.get("status") == "err":
                error_msg = result.get("response", {}).get("data", "Errore sconosciuto")
                return {
                    "status": "error",
                    "message": f"Errore chiusura {exact_symbol}: {error_msg}",
                    "symbol_used": exact_symbol
                }
            
            # Rimuovi dal tracking solo se la chiusura è andata a buon fine
            risk_manager.remove_position(symbol)
            return result

        # OPEN - verifica con risk manager
        can_open = risk_manager.can_open_position(balance_usd)
        if not can_open["allowed"]:
            return {
                "status": "rejected",
                "reason": can_open["reason"]
            }

        # Calcola position size con risk management
        stop_loss_pct = order_json.get("stop_loss_pct", 2.0)
        take_profit_pct = order_json.get("take_profit_pct", 5.0)
        requested_portion = order_json.get("target_portion_of_balance", 0.1)
        leverage = int(order_json.get("leverage", 1))

        sizing = risk_manager.calculate_position_size(
            balance_usd=balance_usd,
            requested_portion=requested_portion,
            stop_loss_pct=stop_loss_pct,
            leverage=leverage
        )

        # Aggiorna order_json con size calcolata
        adjusted_order = order_json.copy()
        adjusted_order["target_portion_of_balance"] = sizing["effective_portion"]

        # Esegui ordine
        result = self.execute_signal(adjusted_order)

        # Assicurati che result sia sempre un dizionario
        if result is None:
            return {"status": "error", "message": "execute_signal returned None"}

        if result.get("status") == "ok" or "statuses" in result:
            # Ottieni prezzo di entry dai mids
            mids = self.info.all_mids()
            entry_price = float(mids.get(symbol, 0))

            # Registra posizione per monitoring
            risk_manager.register_position(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                size=sizing["size_usd"] / entry_price if entry_price > 0 else 0,
                leverage=leverage,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct
            )

            result["risk_management"] = {
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
                "position_size_usd": sizing["size_usd"],
                "risk_usd": sizing["risk_usd"]
            }

        return result

    def get_current_prices(self, symbols: list = None) -> Dict[str, float]:
        """
        Ottiene i prezzi correnti per i simboli specificati.

        Args:
            symbols: Lista di simboli (default: BTC, ETH, SOL)

        Returns:
            Dict {symbol: price}
        """
        if symbols is None:
            symbols = ["BTC", "ETH", "SOL"]

        mids = self.info.all_mids()

        return {
            symbol: float(mids.get(symbol, 0))
            for symbol in symbols
            if symbol in mids
        }

    # ----------------------------------------------------------------------
    #                           UTILITY DEBUG
    # ----------------------------------------------------------------------
    def debug_symbol_limits(self, symbol: str = None):
        """Mostra i limiti di trading per un simbolo o tutti"""
        print("\n📊 LIMITI TRADING HYPERLIQUID")
        print("-" * 60)

        for perp in self.meta["universe"]:
            if symbol and perp["name"] != symbol:
                continue

            print(f"\nSymbol: {perp['name']}")
            print(f"  Min Size: {perp.get('minSz', 'N/A')}")
            print(f"  Size Decimals: {perp.get('szDecimals', 'N/A')}")
            print(f"  Price Decimals: {perp.get('pxDecimals', 'N/A')}")
            print(f"  Max Leverage: {perp.get('maxLeverage', 'N/A')}")
            print(f"  Only Isolated: {perp.get('onlyIsolated', False)}")