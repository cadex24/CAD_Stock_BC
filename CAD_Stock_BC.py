import os
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

app = Flask(__name__)

# ==================== CONFIGURACIÓN ====================

TELEGRAM_TOKEN = "8880757995:AAFre5X-HtkmDr0BYpvHTV0pT6DFIbM6JKg"

# Lista de destinatarios
CHAT_IDS = [
    "7742724655",  # Tu Chat ID
    # "AQUI_EL_CHAT_ID_DE_TU_SRA"  # Chat ID de tu señora
]

URL_MONITOREO = "https://si3.bcentral.cl/siete"

# ==================== FUNCIONES ====================

def en_horario():
    """
    Verifica si estamos en horario de control:
    - Lunes a Viernes
    - 8:00 AM a 7:00 PM (19:00)
    """
    ahora = datetime.now()
    dia_semana = ahora.weekday()
    
    if dia_semana >= 5:
        return False
    
    hora = ahora.hour + ahora.minute / 60.0
    return 8.0 <= hora <= 19.0

def enviar_alerta_telegram(mensaje):
    """
    Envía un mensaje a todos los destinatarios
    """
    for chat_id in CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": mensaje,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"📱 Alerta enviada a {chat_id}", flush=True)
            else:
                print(f"❌ Error enviando a {chat_id}: {response.text}", flush=True)
        except Exception as e:
            print(f"❌ Error: {e}", flush=True)

def verificar_web():
    """
    Verifica el estado de la página web
    """
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

def revisar_web_cada_2min():
    """
    Revisa la web cada 2 minutos (solo en horario)
    """
    if not en_horario():
        if datetime.now().minute == 0:
            print(f"🕒 [OFF] Fuera de horario (8:00-19:00 Lun-Vie)", flush=True)
        return
    
    ahora = datetime.now()
    print(f"🕒 [{ahora.strftime('%H:%M:%S')}] Revisando BDE...", flush=True)
    
    activa, mensaje = verificar_web()
    print(f"   📊 {mensaje}", flush=True)
    
    if not activa:
        alerta = f"""
🚨 *ALERTA INMEDIATA* 🚨

🌐 BDE: OFFLINE 🔴

📌 URL: {URL_MONITOREO}
📊 Estado: {mensaje}
🕐 Hora: {ahora.strftime('%Y-%m-%d %H:%M:%S')}

⚠️ La página del Banco Central no está accesible.
"""
        enviar_alerta_telegram(alerta)

def revisar_web_cada_5min():
    """
    Revisa la web cada 5 minutos (para pruebas)
    Envía alerta confirmando estado (ONLINE u OFFLINE)
    """
    if not en_horario():
        return
    
    ahora = datetime.now()
    print(f"🕐 [{ahora.strftime('%H:%M:%S')}] ALERTA CADA 5 MIN (PRUEBA)", flush=True)
    
    activa, mensaje = verificar_web()
    
    if activa:
        alerta = f"""
✅ *BDE: ONLINE* 🟢 (PRUEBA CADA 5 MIN)

🌐 Banco Central de Chile - SIETE
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora: {ahora.strftime('%Y-%m-%d %H:%M:%S')}

✅ El sistema está funcionando correctamente.
"""
        enviar_alerta_telegram(alerta)
    else:
        alerta = f"""
🚨 *BDE: OFFLINE* 🔴 (PRUEBA CADA 5 MIN)

🌐 Banco Central de Chile - SIETE
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora: {ahora.strftime('%Y-%m-%d %H:%M:%S')}

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
    
    if activa:
        return f"""
📊 *ESTADO DEL MONITOR BDE*

✅ BDE: ONLINE 🟢
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Última revisión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📱 Alertas por: Telegram
👥 Destinatarios: Carl
⏱️ Revisión cada: 2 minutos
⏱️ Alerta cada: 5 minutos (PRUEBA)
🕐 Horario: Lun-Vie 8:00-19:00
"""
    else:
        return f"""
📊 *ESTADO DEL MONITOR BDE*

❌ BDE: OFFLINE 🔴
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Última revisión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📱 Alertas por: Telegram
👥 Destinatarios: Carl
⏱️ Revisión cada: 2 minutos
⏱️ Alerta cada: 5 minutos (PRUEBA)
🕐 Horario: Lun-Vie 8:00-19:00
"""

@app.route("/test")
def test():
    alerta = f"""
🧪 *ALERTA DE PRUEBA*

✅ Este es un mensaje de prueba del BDE Monitor.
🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📱 Las alertas funcionan correctamente.
"""
    enviar_alerta_telegram(alerta)
    return "Alerta de prueba enviada", 200

# ==================== SERVIDOR ====================

# Scheduler para revisión cada 2 minutos
scheduler_2min = BackgroundScheduler()
scheduler_2min.add_job(func=revisar_web_cada_2min, trigger="interval", minutes=2)
scheduler_2min.start()

# Scheduler para alerta cada 5 minutos (PRUEBA)
scheduler_5min = BackgroundScheduler()
scheduler_5min.add_job(func=revisar_web_cada_5min, trigger="interval", minutes=5)
scheduler_5min.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("="*60)
    print("🚀 BDE MONITOR - Banco Central de Chile")
    print("="*60)
    print(f"📌 URL a monitorear: {URL_MONITOREO}")
    print(f"⏱️ Revisión cada: 2 minutos")
    print(f"⏱️ Alerta cada: 5 minutos (PRUEBA)")
    print(f"📱 Alertas por: Telegram")
    print(f"🕐 Horario: Lun-Vie 8:00-19:00")
    print("="*60)
    app.run(host="0.0.0.0", port=port)
    
