import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import warnings
import logging

# Sopprimi warning generici
warnings.filterwarnings('ignore')

# Sopprimi specificamente il warning di convergenza ARIMA da statsmodels
# Questo warning appare quando l'ottimizzazione Maximum Likelihood non converge,
# ma il modello può comunque essere utilizzabile
warnings.filterwarnings('ignore', category=UserWarning, module='statsmodels')
warnings.filterwarnings('ignore', message='.*Maximum Likelihood optimization failed to converge.*')

# Sopprimi specificamente l'errore di prophet.plot per plotly (non è critico)
# Prophet stampa un ERROR quando plotly non è disponibile, ma non è necessario per il funzionamento
# Questo evita il messaggio: "Importing plotly failed. Interactive plots will not work."
prophet_plot_logger = logging.getLogger('prophet.plot')
prophet_plot_logger.setLevel(logging.CRITICAL)
prophet_plot_logger.disabled = True  # Disabilita completamente il logger

# Import Prophet (opzionale)
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    Prophet = None

# Import Hyperliquid (opzionale)
try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
    HYPERLIQUID_AVAILABLE = True
except ImportError:
    HYPERLIQUID_AVAILABLE = False
    Info = None
    constants = None

# Import per modelli ibridi
try:
    from statsmodels.tsa.arima.model import ARIMA
    from sklearn.preprocessing import MinMaxScaler
    import torch
    import torch.nn as nn
    ARIMA_AVAILABLE = True
    TORCH_AVAILABLE = True
except ImportError as e:
    ARIMA_AVAILABLE = False
    TORCH_AVAILABLE = False
    nn = None
    torch = None
    warnings.warn(f"Librerie per modelli ibridi non disponibili: {e}. Userò solo Prophet.")


if TORCH_AVAILABLE and nn is not None:
    class LSTMPredictor(nn.Module):
        """Modello LSTM semplice per previsioni di prezzo"""
        def __init__(self, input_size=1, hidden_size=50, num_layers=2, output_size=1):
            super(LSTMPredictor, self).__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            
            self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
            self.fc = nn.Linear(hidden_size, output_size)
            
        def forward(self, x):
            # x shape: (batch, seq_len, features)
            lstm_out, _ = self.lstm(x)
            # Prendi solo l'ultimo output
            predictions = self.fc(lstm_out[:, -1, :])
            return predictions
else:
    LSTMPredictor = None


class HybridForecaster:
    """Forecaster ibrido che combina ARIMA e LSTM per previsioni più accurate"""
    
    def __init__(self, testnet: bool = True, use_gpu: bool = False):
        if not HYPERLIQUID_AVAILABLE:
            raise ImportError("hyperliquid-python-sdk non è installato. Installalo con: pip install hyperliquid-python-sdk")
        
        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        from hyperliquid_utils import init_info_with_retry
        self.info = init_info_with_retry(base_url, skip_ws=True)
        
        if TORCH_AVAILABLE:
            self.use_gpu = use_gpu and torch.cuda.is_available()
            self.device = torch.device("cuda" if self.use_gpu else "cpu")
        else:
            self.use_gpu = False
            self.device = None
        
        if ARIMA_AVAILABLE:
            from sklearn.preprocessing import MinMaxScaler
            self.scaler = MinMaxScaler()
        else:
            self.scaler = None
        
    def _fetch_candles(self, coin: str, interval: str, limit: int) -> pd.DataFrame:
        """Recupera le candele da Hyperliquid"""
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        interval_ms = {"15m": 15*60_000, "1h": 60*60_000}[interval]
        start_ms = now_ms - limit * interval_ms

        data = self.info.candles_snapshot(
            name=coin,
            interval=interval,
            startTime=start_ms,
            endTime=now_ms
        )

        if not data:
            raise RuntimeError(f"No candles for {coin} {interval}")

        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df["close"] = df["c"].astype(float)

        df = df[["timestamp", "close"]].sort_values("timestamp").reset_index(drop=True)
        return df
    
    def _prepare_lstm_data(self, prices: np.ndarray, sequence_length: int = 20):
        """Prepara i dati per il training LSTM usando sliding window"""
        # Crea uno scaler se non disponibile
        try:
            if self.scaler is None:
                from sklearn.preprocessing import MinMaxScaler
                scaler = MinMaxScaler()
            else:
                scaler = self.scaler
        except ImportError:
            warnings.warn("sklearn non disponibile per normalizzazione LSTM")
            return None, None, None
        
        # Normalizza i prezzi
        prices_scaled = scaler.fit_transform(prices.reshape(-1, 1)).flatten()
        
        X, y = [], []
        for i in range(len(prices_scaled) - sequence_length):
            X.append(prices_scaled[i:i+sequence_length])
            y.append(prices_scaled[i+sequence_length])
        
        return np.array(X), np.array(y), scaler
    
    def _train_lstm(self, prices: np.ndarray, epochs: int = 10, sequence_length: int = 20):
        """Addestra un modello LSTM velocemente"""
        if not TORCH_AVAILABLE or len(prices) < sequence_length + 10:
            return None, None
        
        if self.device is None or LSTMPredictor is None:
            return None, None
        
        try:
            result = self._prepare_lstm_data(prices, sequence_length)
            if result is None or result[0] is None:
                return None, None
            
            X, y, scaler = result
            
            if len(X) < 5:
                return None, None
            
            # Converti in tensori
            X_tensor = torch.FloatTensor(X).unsqueeze(-1).to(self.device)
            y_tensor = torch.FloatTensor(y).unsqueeze(-1).to(self.device)
            
            # Crea e addestra il modello
            model = LSTMPredictor(input_size=1, hidden_size=32, num_layers=1, output_size=1).to(self.device)
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            
            # Training veloce (max 10 secondi)
            model.train()
            for epoch in range(min(epochs, 20)):  # Limita a 20 epoche max
                optimizer.zero_grad()
                outputs = model(X_tensor)
                loss = criterion(outputs, y_tensor)
                loss.backward()
                optimizer.step()
                
                # Early stopping se convergiamo
                if loss.item() < 1e-6:
                    break
            
            return model, scaler
            
        except Exception as e:
            warnings.warn(f"Errore training LSTM: {e}")
            return None, None
    
    def _predict_lstm(self, model, scaler, last_sequence: np.ndarray):
        """Esegue una previsione con LSTM"""
        if model is None or scaler is None:
            return None
        
        try:
            # Normalizza l'ultima sequenza
            last_sequence_scaled = scaler.transform(last_sequence.reshape(-1, 1)).flatten()
            
            # Prepara input
            X = torch.FloatTensor(last_sequence_scaled).unsqueeze(0).unsqueeze(-1).to(self.device)
            
            # Previsione
            model.eval()
            with torch.no_grad():
                prediction_scaled = model(X).cpu().numpy()[0, 0]
            
            # Denormalizza usando inverse_transform
            prediction_array = np.array([[prediction_scaled]])
            prediction = scaler.inverse_transform(prediction_array)[0, 0]
            
            return prediction
        except Exception as e:
            warnings.warn(f"Errore previsione LSTM: {e}")
            return None
    
    def _train_arima(self, prices: np.ndarray, max_p: int = 5, max_d: int = 2, max_q: int = 5):
        """Addestra un modello ARIMA"""
        if not ARIMA_AVAILABLE or len(prices) < 10:
            return None
        
        try:
            # Auto-ARIMA semplificato: prova alcuni parametri comuni
            best_aic = np.inf
            best_model = None
            
            # Parametri comuni per serie finanziarie
            param_combinations = [
                (1, 1, 1), (2, 1, 2), (1, 1, 0), (0, 1, 1),
                (3, 1, 3), (2, 1, 1), (1, 0, 1)
            ]
            
            for p, d, q in param_combinations:
                try:
                    model = ARIMA(prices, order=(p, d, q))
                    fitted_model = model.fit()
                    
                    if fitted_model.aic < best_aic:
                        best_aic = fitted_model.aic
                        best_model = fitted_model
                except:
                    continue
            
            return best_model
        except Exception as e:
            warnings.warn(f"Errore training ARIMA: {e}")
            return None
    
    def _predict_arima(self, model, steps: int = 1):
        """Esegue una previsione con ARIMA"""
        if model is None:
            return None
        
        try:
            forecast = model.forecast(steps=steps)
            return forecast[0] if len(forecast) > 0 else None
        except Exception as e:
            warnings.warn(f"Errore previsione ARIMA: {e}")
            return None
    
    def forecast(self, coin: str, interval: str) -> dict:
        """Esegue previsione ibrida ARIMA + LSTM"""
        # Recupera dati
        if interval == "15m":
            df = self._fetch_candles(coin, "15m", limit=300)
        else:
            df = self._fetch_candles(coin, "1h", limit=500)
        
        prices = df["close"].values
        last_price = prices[-1]
        current_timestamp = df["timestamp"].iloc[-1]
        
        # Addestra modelli
        arima_model = self._train_arima(prices)
        lstm_model, lstm_scaler = self._train_lstm(prices, epochs=15, sequence_length=20)
        
        # Previsioni
        arima_pred = self._predict_arima(arima_model, steps=1)
        
        lstm_pred = None
        if lstm_model is not None and lstm_scaler is not None:
            sequence_length = 20
            if len(prices) >= sequence_length:
                last_sequence = prices[-sequence_length:]
                lstm_pred = self._predict_lstm(lstm_model, lstm_scaler, last_sequence)
        
        # Combina previsioni (media pesata: 60% LSTM, 40% ARIMA se entrambi disponibili)
        if lstm_pred is not None and arima_pred is not None:
            forecast_price = 0.6 * lstm_pred + 0.4 * arima_pred
            model_used = "LSTM+ARIMA"
        elif lstm_pred is not None:
            forecast_price = lstm_pred
            model_used = "LSTM"
        elif arima_pred is not None:
            forecast_price = arima_pred
            model_used = "ARIMA"
        else:
            # Fallback: usa media mobile semplice
            forecast_price = last_price
            model_used = "SMA"
        
        # Calcola variazione percentuale
        pct_change = ((forecast_price - last_price) / last_price) * 100
        
        return {
            "symbol": coin,
            "interval": interval,
            "forecast_price": round(forecast_price, 2),
            "pct_change": round(pct_change, 2),
            "model_used": model_used,
            "last_price": round(last_price, 2),
            "timestamp": current_timestamp
        }
    
    def forecast_many(self, tickers: list, intervals=("15m", "1h")):
        """Esegue previsioni per multiple coppie ticker/interval"""
        results = []
        for coin in tickers:
            for interval in intervals:
                try:
                    result = self.forecast(coin, interval)
                    results.append(result)
                except Exception as e:
                    # Fallback a valori None in caso di errore
                    results.append({
                        "symbol": coin,
                        "interval": interval,
                        "forecast_price": None,
                        "pct_change": None,
                        "model_used": "ERROR",
                        "last_price": None,
                        "timestamp": None,
                        "error": str(e)
                    })
        return results


class HyperliquidForecaster:
    """Forecaster originale con Prophet (usato come fallback)"""
    def __init__(self, testnet: bool = True):
        if not HYPERLIQUID_AVAILABLE:
            raise ImportError("hyperliquid-python-sdk non è installato. Installalo con: pip install hyperliquid-python-sdk")
        if not PROPHET_AVAILABLE:
            raise ImportError("prophet non è installato. Installalo con: pip install prophet")
        
        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        from hyperliquid_utils import init_info_with_retry
        self.info = init_info_with_retry(base_url, skip_ws=True)
        self.last_prices = {}  # Memorizza gli ultimi prezzi per calcolare la variazione

    def _fetch_candles(self, coin: str, interval: str, limit: int) -> pd.DataFrame:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        interval_ms = {"15m": 15*60_000, "1h": 60*60_000}[interval]
        start_ms = now_ms - limit * interval_ms

        data = self.info.candles_snapshot(
            name=coin,
            interval=interval,
            startTime=start_ms,
            endTime=now_ms
        )

        if not data:
            raise RuntimeError(f"No candles for {coin} {interval}")

        df = pd.DataFrame(data)
        df["ds"] = pd.to_datetime(df["t"], unit="ms", utc=True).dt.tz_convert(None)
        df["y"] = df["c"].astype(float)

        df = df[["ds", "y"]].sort_values("ds").reset_index(drop=True)
        return df

    def forecast(self, coin: str, interval: str) -> tuple:
        if interval == "15m":
            df = self._fetch_candles(coin, "15m", limit=300)
            freq = "15min"
        else:
            df = self._fetch_candles(coin, "1h", limit=500)
            freq = "H"

        # Memorizza l'ultimo prezzo
        last_price = df["y"].iloc[-1]

        model = Prophet(daily_seasonality=True, weekly_seasonality=True)
        model.fit(df)

        future = model.make_future_dataframe(periods=1, freq=freq)
        forecast = model.predict(future)

        # Restituisce sia il forecast che l'ultimo prezzo
        return forecast.tail(1)[["ds", "yhat", "yhat_lower", "yhat_upper"]], last_price

    def forecast_many(self, tickers: list, intervals=("15m", "1h")):
        results = []
        for coin in tickers:
            for interval in intervals:
                try:
                    forecast_data, last_price = self.forecast(coin, interval)
                    fc = forecast_data.iloc[0]
                    
                    # Calcola la variazione percentuale
                    variazione_pct = ((fc["yhat"] - last_price) / last_price) * 100
                    
                    # Determina il timeframe in italiano
                    timeframe = "Prossimi 15 Minuti" if interval == "15m" else "Prossima Ora"
                    
                    results.append({
                        "Ticker": coin,
                        "Timeframe": timeframe,
                        "Ultimo Prezzo": round(last_price, 2),
                        "Previsione": round(fc["yhat"], 2),
                        "Limite Inferiore": round(fc["yhat_lower"], 2),
                        "Limite Superiore": round(fc["yhat_upper"], 2),
                        "Variazione %": round(variazione_pct, 2),
                        "Timestamp Previsione": fc["ds"]
                    })
                except Exception as e:
                    results.append({
                        "Ticker": coin,
                        "Timeframe": "Prossimi 15 Minuti" if interval == "15m" else "Prossima Ora",
                        "Ultimo Prezzo": None,
                        "Previsione": None,
                        "Limite Inferiore": None,
                        "Limite Superiore": None,
                        "Variazione %": None,
                        "Timestamp Previsione": None,
                        "error": str(e)
                    })
        return results

    def get_predictions_summary(self) -> pd.DataFrame:
        """Restituisce un DataFrame con il riepilogo delle previsioni (compatibile con il vecchio script)"""
        if not hasattr(self, '_last_results'):
            return pd.DataFrame()
        return pd.DataFrame(self._last_results)

    def get_crypto_forecasts(self, tickers: list):
        """Metodo principale compatibile con il vecchio script"""
        self._last_results = self.forecast_many(tickers, intervals=("15m", "1h"))
        df = pd.DataFrame(self._last_results)
        
        # Rimuovi la colonna error se presente
        if 'error' in df.columns:
            df = df.drop('error', axis=1)
            
        return df.to_string(index=False)


def _format_forecast_text(results: list) -> str:
    """Formatta i risultati come tabella testo"""
    if not results:
        return "Nessuna previsione disponibile"
    
    # Header
    lines = ["| Asset | Timeframe | Forecast Price | % Change | Model |"]
    lines.append("|-------|-----------|----------------|----------|--------|")
    
    for r in results:
        if r.get("forecast_price") is None:
            continue
        
        symbol = r.get("symbol", "N/A")
        interval = r.get("interval", "N/A")
        forecast_price = r.get("forecast_price", 0)
        pct_change = r.get("pct_change", 0)
        model_used = r.get("model_used", "N/A")
        
        # Formatta variazione percentuale con segno
        pct_str = f"{pct_change:+.2f}%" if pct_change is not None else "N/A"
        
        lines.append(f"| {symbol} | {interval} | {forecast_price} | {pct_str} | {model_used} |")
    
    return "\n".join(lines)


def _convert_to_legacy_format(results: list) -> list:
    """Converte il nuovo formato al formato legacy per compatibilità"""
    legacy_results = []
    for r in results:
        interval = r.get("interval", "")
        timeframe = "Prossimi 15 Minuti" if interval == "15m" else "Prossima Ora"
        
        legacy_results.append({
            "Ticker": r.get("symbol", ""),
            "Timeframe": timeframe,
            "Ultimo Prezzo": r.get("last_price"),
            "Previsione": r.get("forecast_price"),
            "Limite Inferiore": None,  # Non disponibile nel nuovo modello
            "Limite Superiore": None,  # Non disponibile nel nuovo modello
            "Variazione %": r.get("pct_change"),
            "Timestamp Previsione": r.get("timestamp")
        })
    return legacy_results


# Funzione helper per mantenere compatibilità con il vecchio script
def get_hyperliquid_forecasts(tickers=['BTC', 'ETH', 'SOL'], testnet=True):
    forecaster = HyperliquidForecaster(testnet=testnet)
    return forecaster.get_crypto_forecasts(tickers)


def get_crypto_forecasts(tickers=['BTC', 'ETH', 'SOL'], testnet=True, use_hybrid=True):
    """
    Funzione principale per ottenere previsioni crypto.
    
    Args:
        tickers: Lista di ticker da analizzare
        testnet: Se usare testnet o mainnet
        use_hybrid: Se True, usa HybridForecaster (LSTM+ARIMA), altrimenti usa Prophet
    
    Returns:
        tuple: (text_forecast, json_forecast)
    """
    try:
        if use_hybrid and ARIMA_AVAILABLE and TORCH_AVAILABLE and HYPERLIQUID_AVAILABLE:
            # Usa il nuovo forecaster ibrido
            try:
                forecaster = HybridForecaster(testnet=testnet)
                results = forecaster.forecast_many(tickers, intervals=("15m", "1h"))
                
                # Formatta output
                text_output = _format_forecast_text(results)
                
                # Crea JSON nel formato richiesto
                json_output = [
                    {
                        "symbol": r.get("symbol"),
                        "interval": r.get("interval"),
                        "forecast_price": r.get("forecast_price"),
                        "pct_change": r.get("pct_change"),
                        "model_used": r.get("model_used")
                    }
                    for r in results
                ]
                
                return text_output, json_output
            except Exception as e:
                warnings.warn(f"Errore con HybridForecaster: {e}. Fallback a Prophet.")
                # Continua con il fallback
        
        # Fallback a Prophet
        if not PROPHET_AVAILABLE or not HYPERLIQUID_AVAILABLE:
            error_msg = "Nessun modello disponibile. "
            if not PROPHET_AVAILABLE:
                error_msg += "Prophet non installato. "
            if not HYPERLIQUID_AVAILABLE:
                error_msg += "Hyperliquid SDK non installato. "
            error_msg += "Installa le dipendenze necessarie."
            return error_msg, []
        
        if not use_hybrid:
            warnings.warn("Usando Prophet (use_hybrid=False)")
        else:
            warnings.warn("Librerie per modelli ibridi non disponibili. Fallback a Prophet.")
        
        forecaster = HyperliquidForecaster(testnet=testnet)
        results = forecaster.forecast_many(tickers, intervals=("15m", "1h"))
        
        # Converti al formato richiesto
        df = pd.DataFrame(results)
        
        # Crea output testo nel nuovo formato
        text_lines = ["| Asset | Timeframe | Forecast Price | % Change | Model |"]
        text_lines.append("|-------|-----------|----------------|----------|--------|")
        
        for _, row in df.iterrows():
            if pd.isna(row.get("Previsione")):
                continue
            
            symbol = row.get("Ticker", "N/A")
            interval = "15m" if "15 Minuti" in str(row.get("Timeframe", "")) else "1h"
            forecast_price = row.get("Previsione", 0)
            pct_change = row.get("Variazione %", 0)
            
            pct_str = f"{pct_change:+.2f}%" if not pd.isna(pct_change) else "N/A"
            text_lines.append(f"| {symbol} | {interval} | {forecast_price} | {pct_str} | Prophet |")
        
        text_output = "\n".join(text_lines)
        
        # Crea JSON
        json_output = [
            {
                "symbol": row.get("Ticker"),
                "interval": "15m" if "15 Minuti" in str(row.get("Timeframe", "")) else "1h",
                "forecast_price": row.get("Previsione"),
                "pct_change": row.get("Variazione %"),
                "model_used": "Prophet"
            }
            for _, row in df.iterrows()
        ]
        
        return text_output, json_output
            
    except Exception as e:
        warnings.warn(f"Errore in get_crypto_forecasts: {e}")
        # Fallback finale
        try:
            forecaster = HyperliquidForecaster(testnet=testnet)
            results = forecaster.forecast_many(tickers, intervals=("15m", "1h"))
            df = pd.DataFrame(results)
            return df.to_string(index=False), df.to_json(orient='records')
        except:
            return "Forecast non disponibili", []


# Esempio di utilizzo
# if __name__ == "__main__":
#     print(get_crypto_forecasts())
