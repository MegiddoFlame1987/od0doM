"""Cienka warstwa nad Alpaca. Tylko konto paper: paper=True jest wpisane na sztywno."""
import os
from datetime import datetime


class AlpacaPaperBroker:
    def __init__(self):
        from alpaca.trading.client import TradingClient
        from alpaca.data.historical import StockHistoricalDataClient
        key = os.environ["ALPACA_API_KEY"]
        secret = os.environ["ALPACA_SECRET_KEY"]
        self.trading = TradingClient(key, secret, paper=True)
        self.data = StockHistoricalDataClient(key, secret)

    def session_close(self, day):
        """Godzina zamknięcia sesji (ET) albo None, gdy giełda nieczynna."""
        from alpaca.trading.requests import GetCalendarRequest
        from common import ET
        cal = self.trading.get_calendar(GetCalendarRequest(start=day, end=day))
        if not cal or str(cal[0].date) != day.isoformat():
            return None
        close = cal[0].close
        if isinstance(close, datetime):
            close = (close.astimezone(ET) if close.tzinfo else close).time()
        return close

    def open_position_symbols(self) -> list:
        return [p.symbol for p in self.trading.get_all_positions()]

    def latest_prices(self, symbols: list) -> dict:
        from alpaca.data.requests import StockLatestTradeRequest
        from alpaca.data.enums import DataFeed
        res = self.data.get_stock_latest_trade(
            StockLatestTradeRequest(symbol_or_symbols=symbols, feed=DataFeed.IEX))
        return {s: float(res[s].price) for s in symbols}

    def submit(self, symbol: str, qty: int, side: str, when: str) -> str:
        """side: 'buy'/'sell'; when: 'open' (aukcja otwarcia) albo 'close' (aukcja zamknięcia)."""
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        order = self.trading.submit_order(MarketOrderRequest(
            symbol=symbol, qty=qty,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.OPG if when == "open" else TimeInForce.CLS))
        return str(order.id)

    def fill(self, order_id: str) -> dict:
        o = self.trading.get_order_by_id(order_id)
        status = getattr(o.status, "value", str(o.status))
        return {"status": status,
                "cena": float(o.filled_avg_price) if o.filled_avg_price else None,
                "ilosc": int(float(o.filled_qty or 0))}
