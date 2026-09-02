import os
import requests
import yfinance as yf
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8995245953:AAGEZZr-KnwItSMe7n5Ys-8m1PRuP0DVukA")

ULTIMO_CHAT_ID = None
MI_CARTERA = {}
ESTADO_ALERTAS = {}
ESTADO_USUARIO = {}  # Para el flujo de /consultas

TICKERS_INTERES = [
    "BCI", "BSANTANDER", "CAP", "CENCOSUD", "CHILE",
    "CMPC", "COPEC", "ENTEL", "QUINENCO",
    "SQM-B", "VAPORES", "SMSAAM", "LTM", "ITAUCL", "BESALCO"
]

# ==================== FUNCIÓN DE HORA CHILE ====================

def get_hora_chile():
    return datetime.now() - timedelta(hours=4)

def get_hora_chile_str():
    return get_hora_chile().strftime('%H:%M:%S')

# ==================== FUNCIONES DE DATOS ====================

def obtener_datos_accion(ticker_limpio):
    try:
        ticker = f"{ticker_limpio}.SN"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        
        if hist.empty:
            return None, None, None, None
        
        p_act = float(hist['Close'].iloc[-1])
        p_apertura = float(hist['Open'].iloc[0])
        p_min = float(hist['Low'].min())
        p_max = float(hist['High'].max())
        
        return p_act, p_apertura, p_min, p_max
    except Exception as e:
        print(f"Error en {ticker_limpio}: {e}", flush=True)
        return None, None, None, None

def obtener_resumen_general():
    texto = "📊 *MERCADO CHILENO*\n"
    texto += "─" * 20 + "\n\n"
    contador = 0
    
    for ticker in TICKERS_INTERES:
        datos = obtener_datos_accion(ticker)
        if datos and datos[0]:
            p_act, p_apertura, _, _ = datos
            var = ((p_act - p_apertura) / p_apertura) * 100 if p_apertura > 0 else 0
            
            if var > 0:
                icono = "▴"
                color = "🟢"
            elif var < 0:
                icono = "▾"
                color = "🔴"
            else:
                icono = "—"
                color = "⚪"
            
            texto += f"{color} *{ticker}*  {icono} {var:+.2f}%\n"
            texto += f"   ${p_act:,.2f}  (apertura ${p_apertura:,.2f})\n\n"
            contador += 1
            
    return texto if contador > 0 else "⚠️ No se pudo obtener información del mercado."

def consultar_accion(ticker_input):
    ticker_limpio = ticker_input.upper().replace(".SN", "").strip()
    datos = obtener_datos_accion(ticker_limpio)
    
    if datos and datos[0]:
        p_act, p_apertura, p_min, p_max = datos
        var = ((p_act - p_apertura) / p_apertura) * 100 if p_apertura > 0 else 0
        
        if var > 0:
            estado = "🟢 Alcista"
        elif var < 0:
            estado = "🔴 Bajista"
        else:
            estado = "⚪ Sin cambios"
        
        texto = f"🔍 *{ticker_limpio}*\n"
        texto += "─" * 15 + "\n\n"
        texto += f"💰 Precio  :  ${p_act:,.2f}\n"
        texto += f"📊 Apertura :  ${p_apertura:,.2f}\n"
        texto += f"📈 Variación:  {var:+.2f}%\n"
        texto += f"📉 Mínimo   :  ${p_min:,.2f}\n"
        texto += f"📈 Máximo   :  ${p_max:,.2f}\n\n"
        texto += f"▸ {estado}"
        
        if var >= 2.0:
            texto += "  ⚡ alza"
        elif var <= -2.0:
            texto += "  ⚡ baja"
        
        return texto
                
    return f"❌ No se encontró información para `{ticker_limpio}`."

def consultar_cartera():
    if not MI_CARTERA:
        return "📭 No tienes cartera configurada."
        
    texto = "💼 *CARTERA*\n"
    texto += "─" * 15 + "\n\n"
    total_valor = 0
    total_inversion = 0
    
    for ticker, datos_c in MI_CARTERA.items():
        cant = datos_c["cantidad"]
        p_compra = datos_c["precio_compra"]
        ticker_limpio = ticker.replace(".SN", "").upper()
        
        datos = obtener_datos_accion(ticker_limpio)
        if datos and datos[0]:
            p_act = datos[0]
            val_actual = cant * p_act
            val_inicial = cant * p_compra
            pnl = val_actual - val_inicial
            pnl_porc = (pnl / val_inicial) * 100 if val_inicial > 0 else 0
            
            total_valor += val_actual
            total_inversion += val_inicial
            
            if pnl > 0:
                icono = "🟢"
            elif pnl < 0:
                icono = "🔴"
            else:
                icono = "⚪"
            
            texto += f"{icono} *{ticker_limpio}*  {cant} un.\n"
            texto += f"   ${p_act:,.2f}  |  {pnl_porc:+.2f}%  |  ${pnl:+,.2f}\n\n"
            
    pnl_total = total_valor - total_inversion
    pnl_total_porc = (pnl_total / total_inversion) * 100 if total_inversion > 0 else 0
    
    texto += "─" * 15 + "\n"
    texto += f"💰 Total    :  ${total_valor:,.2f}\n"
    texto += f"📈 PnL Total:  {pnl_total_porc:+.2f}%  (${pnl_total:+,.2f})"
    return texto

# ==================== HORARIO Y ALERTAS ====================

def en_horario_mercado():
    hora_chile = get_hora_chile()
    dia_semana = hora_chile.weekday()
    if dia_semana >= 5:
        return False
    hora = hora_chile.hour + hora_chile.minute / 60.0
    return 9.0 <= hora <= 16.1667

def enviar_alerta(ticker, p_act, p_apertura, var, direccion):
    global ULTIMO_CHAT_ID, TELEGRAM_TOKEN
    
    if direccion == "subida":
        titulo = "🟢 ALERTA DE SUBIDA"
        mensaje = "▸ Superó el +2% desde apertura"
    else:
        titulo = "🔴 ALERTA DE BAJADA"
        mensaje = "▸ Superó el -2% desde apertura"
    
    hora_chile = get_hora_chile_str()
    
    alerta = f"""
🚨 *{titulo}* 🚨

📌 *{ticker}*

💰 ${p_act:,.2f}
📊 Apertura: ${p_apertura:,.2f}
📈 Variación: *{var:+.2f}%*

{mensaje}

🕐 {hora_chile}
"""
    
    url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": ULTIMO_CHAT_ID, "text": alerta, "parse_mode": "Markdown"}
    requests.post(url_api, json=payload)

def revisar_alertas_mercado():
    global ULTIMO_CHAT_ID, ESTADO_ALERTAS
    
    if not en_horario_mercado():
        return
    
    if not ULTIMO_CHAT_ID:
        return

    for ticker in TICKERS_INTERES:
        try:
            datos = obtener_datos_accion(ticker)
            if not datos or not datos[0]:
                continue
                
            p_act, p_apertura, _, _ = datos
            var = ((p_act - p_apertura) / p_apertura) * 100 if p_apertura > 0 else 0
            
            if ticker not in ESTADO_ALERTAS:
                ESTADO_ALERTAS[ticker] = {"activa": False, "direccion": None}
            
            if abs(var) >= 2.0:
                if ESTADO_ALERTAS[ticker]["activa"]:
                    if ESTADO_ALERTAS[ticker]["direccion"] == "subida" and var <= -2.0:
                        ESTADO_ALERTAS[ticker]["direccion"] = "bajada"
                        enviar_alerta(ticker, p_act, p_apertura, var, "bajada")
                    elif ESTADO_ALERTAS[ticker]["direccion"] == "bajada" and var >= 2.0:
                        ESTADO_ALERTAS[ticker]["direccion"] = "subida"
                        enviar_alerta(ticker, p_act, p_apertura, var, "subida")
                else:
                    ESTADO_ALERTAS[ticker]["activa"] = True
                    if var >= 2.0:
                        ESTADO_ALERTAS[ticker]["direccion"] = "subida"
                        enviar_alerta(ticker, p_act, p_apertura, var, "subida")
                    else:
                        ESTADO_ALERTAS[ticker]["direccion"] = "bajada"
                        enviar_alerta(ticker, p_act, p_apertura, var, "bajada")
            else:
                ESTADO_ALERTAS[ticker]["activa"] = False
                ESTADO_ALERTAS[ticker]["direccion"] = None
                    
        except Exception as e:
            print(f"Error en alerta {ticker}: {e}", flush=True)

scheduler = BackgroundScheduler()
scheduler.add_job(func=revisar_alertas_mercado, trigger="interval", minutes=2)
scheduler.start()

@app.route("/")
def index():
    return "🟢 Bot de Mercado Chileno Activo", 200

@app.route("/estado")
def estado():
    hora_chile = get_hora_chile_str()
    return f"""
📊 *ESTADO DEL BOT*

✅ Activo
🕐 {hora_chile}
👤 {ULTIMO_CHAT_ID if ULTIMO_CHAT_ID else "No configurado"}
⏱️ Cada 2 min  |  Lun-Vie 9:00-16:10
📊 Alertas: +/- 2% vs apertura
""", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook_telegram():
    global ULTIMO_CHAT_ID, ESTADO_USUARIO
    
    try:
        update_json = request.get_json(force=True)
        
        if "message" in update_json:
            chat_id = update_json["message"]["chat"]["id"]
            ULTIMO_CHAT_ID = chat_id
            text = update_json["message"].get("text", "").strip().lower()
            
            print(f"📩 Mensaje recibido de {chat_id}: {text}", flush=True)
            
            # ============ NUEVO COMANDO: /consultas ============
            if text == "/consultas":
                ESTADO_USUARIO[chat_id] = "esperando_opcion_consulta"
                
                respuesta = """
📋 *Selecciona una consulta para enviar:*

1️⃣ ¿Cómo está el mercado hoy?
2️⃣ ¿Qué acciones recomiendas?
3️⃣ ¿Cuál es el rendimiento de mi cartera?

Responde con el número de la opción (1, 2 o 3).
"""
                url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {"chat_id": chat_id, "text": respuesta, "parse_mode": "Markdown"}
                requests.post(url_api, json=payload)
            
            # ============ MANEJAR RESPUESTA DE OPCIÓN ============
            elif ESTADO_USUARIO.get(chat_id) == "esperando_opcion_consulta":
                if text in ["1", "2", "3"]:
                    opciones = {
                        "1": "How is the market today?",
                        "2": "Which stocks do you recommend?",
                        "3": "What is the performance of my portfolio?"
                    }
                    mensaje = opciones[text]
                    
                    # Responder al usuario con la consulta seleccionada
                    respuesta = f"✅ Has seleccionado:\n\n*{mensaje}*"
                    url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    payload = {"chat_id": chat_id, "text": respuesta, "parse_mode": "Markdown"}
                    requests.post(url_api, json=payload)
                    
                    # Limpiar estado
                    ESTADO_USUARIO[chat_id] = None
                else:
                    url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    payload = {"chat_id": chat_id, "text": "⚠️ Opción inválida. Responde con 1, 2 o 3.", "parse_mode": "Markdown"}
                    requests.post(url_api, json=payload)
            
            elif text == "resumen":
                respuesta = obtener_resumen_general()
                url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {"chat_id": chat_id, "text": respuesta, "parse_mode": "Markdown"}
                requests.post(url_api, json=payload)
                
            elif text == "cartera":
                respuesta = consultar_cartera()
                url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {"chat_id": chat_id, "text": respuesta, "parse_mode": "Markdown"}
                requests.post(url_api, json=payload)
                
            else:
                respuesta = consultar_accion(text)
                url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {"chat_id": chat_id, "text": respuesta, "parse_mode": "Markdown"}
                requests.post(url_api, json=payload)
                    
    except Exception as e:
        print(f"Error en webhook: {e}", flush=True)
        
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("="*60)
    print("🚀 BOT DE MERCADO CHILENO")
    print("="*60)
    print(f"⏱️ Revisión cada: 2 minutos")
    print(f"🕐 Horario: Lun-Vie 9:00-16:10 (hora Chile)")
    print(f"📈 Acciones: {len(TICKERS_INTERES)} monitoreadas")
    print("="*60)
    app.run(host="0.0.0.0", port=port)
