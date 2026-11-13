# Bot de trading OKX (modo simulado)

Bot de spot para **OKX Demo Trading**: opera con dinero ficticio. Usa un cruce de medias móviles (SMA rápida/lenta) sobre velas cerradas.

## Cómo funciona

1. En cada vela cerrada calcula la SMA rápida (9) y la lenta (21).
2. **Compra** `ORDER_USDT` a mercado cuando la rápida cruza por encima de la lenta y no hay posición.
3. **Vende** toda la posición cuando la rápida cruza por debajo.
4. Cada vela se procesa una sola vez; los errores de red se reintentan en el siguiente ciclo.

`make_exchange()` activa el modo sandbox de ccxt (cabecera `x-simulated-trading: 1`) y se niega a arrancar si no está activo.

## Puesta en marcha

1. En OKX: **Trading → Demo Trading**, y luego **Perfil → API de Demo Trading → Crear API key** (permiso *Trade*, nunca *Withdraw*).
2. Instalar y configurar:
   ```bash
   cd trading-bot
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # pega aquí las claves de demo
   ```
3. Ejecutar:
   ```bash
   python bot.py --once --dry-run   # comprueba conexión y señal sin enviar órdenes
   python bot.py                    # bucle continuo en la cuenta demo
   ```
4. Tests (sin conexión): `pytest -q`

### En Android (Termux)

`pip install -r requirements.txt` falla en Termux porque ccxt intenta compilar extras (`coincurve`, `orjson`, `uvloop`...) que el bot no usa. Instálalo así:

```bash
pkg install -y python python-cryptography
pip install --no-deps ccxt
pip install requests certifi typing_extensions python-dotenv pytest
```

## Configuración (`.env`)

| Variable | Por defecto | Descripción |
|---|---|---|
| `SYMBOL` | `BTC/USDT` | Par de spot |
| `TIMEFRAME` | `5m` | Temporalidad de las velas |
| `SMA_FAST` / `SMA_SLOW` | `9` / `21` | Periodos de las medias |
| `ORDER_USDT` | `100` | USDT por compra |
| `MIN_POSITION_USDT` | `5` | Umbral para considerar que hay posición |

> Estrategia de ejemplo, no un consejo de inversión. Un cruce de medias simple suele perder dinero después de comisiones en mercados laterales.
