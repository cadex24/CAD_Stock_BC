import os
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

app = Flask(__name__)

# ==================== CONFIGURACIÓN ====================

TELEGRAM_TOKEN = "8880757995:AAGNTQuFhZ4uE7sISDxspnHSze1PNk7HWQA"

CHAT_IDS = {
    "carl": "7742724655",
    "romina": "8834565828"
}

URL_MONITOREO = "https://si3.bcentral.cl/siete"

# ==================== FUNCIÓN DE HORA CHILE ====================

def get_hora_chile():
    """Retorna la hora actual en Chile (UTC-4)"""
    return datetime.now() - timedelta(hours=4)

def get_hora_chile_str():
    """Retorna la hora actual en Chile formateada"""
    return get_hora_chile().strftime('%H:%M:%S')

# ==================== FUNCIONES ====================

def en_horario():
    """Verifica si estamos en horario de control (hora Chile)"""
    hora_chile = get_hora_chile()
    dia_semana = hora_chile.weekday()
    if dia_semana >= 5:
        return False
    hora = hora_chile.hour + hora_chile.minute / 60.0
    return 8.5 <= hora <= 18.75  # 8:30 AM a 6:45 PM

def enviar_mensaje_telegram(chat_id, mensaje):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}", flush=True)
        return False

def enviar_alerta_telegram(mensaje):
    for nombre, chat_id in CHAT_IDS.items():
        enviar_mensaje_telegram(chat_id, mensaje)

def verificar_web():
    try:
        response = requests.get(URL_MONITOREO, timeout=10)
        if response.status_code == 200:
            return True, "✅ BDE: ONLINE 🟢"
        else:
            return False, f"⚠️ BDE: OFFLINE 🔴 (Código: {response.status_code})"
    except requests.exceptions.Timeout:
        return False, "❌ BDE: OFFLINE 🔴 (Timeout)"
    except requests.exceptions.ConnectionError:
        return False, "❌ BDE: OFFLINE 🔴 (Error de conexión)"
    except Exception as e:
        return False, f"❌ BDE: OFFLINE 🔴 (Error: {str(e)})"

def revisar_web_cada_30s():
    """Revisa la web cada 30 segundos (solo en horario)"""
    if not en_horario():
        return
    
    hora_str = get_hora_chile_str()
    print(f"🕒 [{hora_str}] Revisando BDE...", flush=True)
    
    activa, mensaje = verificar_web()
    print(f"   📊 {mensaje}", flush=True)
    
    if not activa:
        alerta = f"""
🚨 *ALERTA INMEDIATA* 🚨

🌐 BDE: OFFLINE 🔴

📌 URL: {URL_MONITOREO}
📊 Estado: {mensaje}
🕐 Hora Chile: {hora_str}

⚠️ La página del Banco Central no está accesible.
"""
        enviar_alerta_telegram(alerta)

def revisar_web_horaria(hora_str):
    """Envía alerta horaria a una hora específica"""
    if not en_horario():
        return
    
    print(f"🕐 [{hora_str}] ALERTA HORARIA - Verificando BDE...", flush=True)
    
    activa, mensaje = verificar_web()
    
    if activa:
        alerta = f"""
✅ *BDE: ONLINE* 🟢

🌐 Banco Central de Chile (SIETE)
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora Chile: {hora_str}

✅ El sistema está funcionando correctamente.
"""
        enviar_alerta_telegram(alerta)
    else:
        alerta = f"""
🚨 *BDE: OFFLINE* 🔴

🌐 Banco Central de Chile (SIETE)
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora Chile: {hora_str}

⚠️ La página del Banco Central no está accesible.
"""
        enviar_alerta_telegram(alerta)

# ==================== RUTAS ====================

@app.route("/")
def index():
    return "🟢 BDE Monitor - Banco Central de Chile", 200

@app.route("/estado")
def estado():
    activa, mensaje = verificar_web()
    hora_chile = get_hora_chile_str()
    
    if activa:
        return f"""
📊 *ESTADO DEL MONITOR BDE*

✅ BDE: ONLINE 🟢
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora Chile: {hora_chile}
📱 Alertas por: Telegram
👥 Destinatarios: Carl y Romina
⏱️ Revisión cada: 30 segundos
⏱️ Alerta horaria: Cada 1 hora (8:30-18:45)
🕐 Horario: Lun-Vie 8:30-18:45 (hora Chile)
"""
    else:
        return f"""
📊 *ESTADO DEL MONITOR BDE*

❌ BDE: OFFLINE 🔴
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora Chile: {hora_chile}
📱 Alertas por: Telegram
👥 Destinatarios: Carl y Romina
⏱️ Revisión cada: 30 segundos
⏱️ Alerta horaria: Cada 1 hora (8:30-18:45)
🕐 Horario: Lun-Vie 8:30-18:45 (hora Chile)
"""

@app.route("/test")
def test():
    hora_chile = get_hora_chile_str()
    alerta = f"""
🧪 *ALERTA DE PRUEBA*

✅ Este es un mensaje de prueba del BDE Monitor.
🕐 Hora Chile: {hora_chile}

📱 Las alertas funcionan correctamente.
"""
    enviar_alerta_telegram(alerta)
    return "Alerta de prueba enviada", 200

# ==================== WEBHOOK DE TELEGRAM ====================

estado_usuario = {}

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook_telegram():
    try:
        update_json = request.get_json(force=True)
        
        if "message" in update_json:
            chat_id = update_json["message"]["chat"]["id"]
            text = update_json["message"].get("text", "").strip()
            
            print(f"📩 Mensaje recibido de {chat_id}: {text}", flush=True)
            
            if str(chat_id) not in CHAT_IDS.values():
                enviar_mensaje_telegram(chat_id, "⚠️ No estás autorizado para usar este bot.")
                return "OK", 200
            
            # ============ COMANDO /encuesta ============
            if text == "/encuesta":
                estado_usuario[chat_id] = "seleccionando_pregunta"
                
                respuesta = """
📋 *Selecciona la pregunta que quieres enviar a Romina:*

1️⃣ Is the service good or bad? (responde con 1 si es good, 2 si es bad)

2️⃣ Describe your experience with the service (máximo 80 caracteres)

3️⃣ Please rate the service from 1 to 7

Responde con el número de la opción (1, 2 o 3).
"""
                enviar_mensaje_telegram(chat_id, respuesta)
            
            # ============ MANEJAR SELECCIÓN DE PREGUNTA ============
            elif estado_usuario.get(chat_id) == "seleccionando_pregunta":
                if text in ["1", "2", "3"]:
                    preguntas = {
                        "1": "Is the service good or bad? (responde con 1 si es good, 2 si es bad)",
                        "2": "Describe your experience with the service (máximo 80 caracteres)",
                        "3": "Please rate the service from 1 to 7"
                    }
                    pregunta = preguntas[text]
                    
                    estado_usuario[chat_id] = f"esperando_respuesta_{text}"
                    estado_usuario[CHAT_IDS["romina"]] = f"respondiendo_pregunta_{text}"
                    
                    enviar_mensaje_telegram(
                        CHAT_IDS["romina"],
                        f"📋 *Pregunta de CAD_Stock_BC:*\n\n{pregunta}"
                    )
                    
                    enviar_mensaje_telegram(
                        chat_id,
                        f"✅ *Pregunta {text} enviada a Romina* 📋\n\n{pregunta}"
                    )
                else:
                    enviar_mensaje_telegram(
                        chat_id,
                        "⚠️ Opción inválida. Responde con 1, 2 o 3."
                    )
            
            # ============ MANEJAR RESPUESTA DE ROMINA ============
            elif str(chat_id) == CHAT_IDS["romina"]:
                if estado_usuario.get(chat_id) and estado_usuario[chat_id].startswith("respondiendo_pregunta_") and not text.startswith("/"):
                    num_pregunta = estado_usuario[chat_id].replace("respondiendo_pregunta_", "")
                    
                    enviar_mensaje_telegram(
                        CHAT_IDS["carl"],
                        f"📩 *Respuesta de Romina a la pregunta {num_pregunta}:*\n\n{text}\n\n🕐 {get_hora_chile_str()}"
                    )
                    enviar_mensaje_telegram(
                        chat_id,
                        "✅ ¡Gracias por tu respuesta! Se la he enviado a Carl. 🙏"
                    )
                    estado_usuario[chat_id] = None
            
            # ============ COMANDO /recordar ============
            elif text.startswith("/recordar"):
                partes = text.split(" ", 1)
                if len(partes) > 1:
                    mensaje = partes[1]
                    enviar_mensaje_telegram(
                        CHAT_IDS["romina"],
                        f"CAD_Stock_BC: {mensaje}"
                    )
                    enviar_mensaje_telegram(
                        chat_id,
                        f"✅ Recordatorio enviado a Romina: {mensaje}"
                    )
                else:
                    enviar_mensaje_telegram(
                        chat_id,
                        "⚠️ Debes escribir un mensaje. Ejemplo:\n`/recordar Pagar la luz`"
                    )
            
            elif text == "/start":
                respuesta = """
🤖 *BDE Monitor - Banco Central de Chile*

✅ Bot activo
📌 Monitoreando: https://si3.bcentral.cl/siete

*Comandos disponibles:*
/estado - Ver estado del BDE
/test - Probar alertas
/recordar [texto] - Enviar recordatorio a Romina
/encuesta - Seleccionar y enviar una pregunta a Romina
"""
                enviar_mensaje_telegram(chat_id, respuesta)
                
            elif text == "/estado":
                activa, mensaje = verificar_web()
                hora_chile = get_hora_chile_str()
                
                if activa:
                    respuesta = f"""
📊 *ESTADO BDE*

✅ BDE: ONLINE 🟢
📌 URL: {URL_MONITOREO}
🕐 Hora Chile: {hora_chile}
"""
                else:
                    respuesta = f"""
📊 *ESTADO BDE*

❌ BDE: OFFLINE 🔴
📌 URL: {URL_MONITOREO}
🕐 Hora Chile: {hora_chile}
"""
                enviar_mensaje_telegram(chat_id, respuesta)
                
            elif text == "/test":
                hora_chile = get_hora_chile_str()
                respuesta = f"""
🧪 *ALERTA DE PRUEBA*

✅ Este es un mensaje de prueba del BDE Monitor.
🕐 Hora Chile: {hora_chile}

📱 Las alertas funcionan correctamente.
"""
                enviar_mensaje_telegram(chat_id, respuesta)
                
            else:
                respuesta = """
🤖 Comandos disponibles:
/estado - Ver estado del BDE
/test - Probar alertas
/recordar [texto] - Enviar recordatorio a Romina
/encuesta - Seleccionar y enviar una pregunta a Romina
"""
                enviar_mensaje_telegram(chat_id, respuesta)
                
    except Exception as e:
        print(f"❌ Error en webhook: {e}", flush=True)
        
    return "OK", 200

# ==================== SERVIDOR ====================

def programar_alertas_horarias():
    """Programa alertas horarias fijas: 8:30, 9:30, 10:30...18:30"""
    horas = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    
    ahora = get_hora_chile()
    hoy = ahora.date()
    
    for hora in horas:
        # Crear la hora de alerta en hora Chile
        hora_alerta = datetime(hoy.year, hoy.month, hoy.day, hora, 30, 0)
        
        # Si la hora ya pasó hoy, programar para mañana
        if ahora >= hora_alerta:
            hora_alerta = hora_alerta + timedelta(days=1)
        
        # Calcular el tiempo hasta la alerta
        tiempo_restante = (hora_alerta - ahora).total_seconds()
        
        # Programar la alerta
        scheduler_horaria.add_job(
            func=revisar_web_horaria,
            trigger="date",
            run_date=hora_alerta,
            args=[hora_alerta.strftime('%H:%M')]
        )

# Scheduler para revisión cada 30 segundos
scheduler_30s = BackgroundScheduler()
scheduler_30s.add_job(func=revisar_web_cada_30s, trigger="interval", seconds=30)
scheduler_30s.start()

# Scheduler para alertas horarias fijas
scheduler_horaria = BackgroundScheduler()
programar_alertas_horarias()
scheduler_horaria.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("="*60)
    print("🚀 BDE MONITOR - Banco Central de Chile")
    print("="*60)
    print(f"📌 URL a monitorear: {URL_MONITOREO}")
    print(f"⏱️ Revisión cada: 30 segundos")
    print(f"⏱️ Alertas horarias: 8:30, 9:30, 10:30...18:30")
    print(f"📱 Alertas por: Telegram")
    print(f"👥 Destinatarios: Carl y Romina")
    print(f"🕐 Horario: Lun-Vie 8:30-18:45 (hora Chile)")
    print("="*60)
    app.run(host="0.0.0.0", port=port)
