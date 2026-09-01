import os
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

app = Flask(__name__)

# ==================== CONFIGURACIÓN ====================

TELEGRAM_TOKEN = "8880757995:AAFre5X-HtkmDr0BYpvHTV0pT6DFIbM6JKg"

# Lista de destinatarios
CHAT_IDS = [
    "7742724655",  # Tu Chat ID
    # "AQUI_EL_CHAT_ID_DE_TU_SRA"  # Chat ID de tu señora
]

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
    """
    Verifica si estamos en horario de control:
    - Lunes a Viernes
    - 8:30 AM a 6:30 PM (18:30) hora Chile
    """
    hora_chile = get_hora_chile()
    dia_semana = hora_chile.weekday()
    
    if dia_semana >= 5:
        return False
    
    hora = hora_chile.hour + hora_chile.minute / 60.0
    return 8.5 <= hora <= 18.5

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
            hora_chile = get_hora_chile_str()
            print(f"🕒 [OFF] Fuera de horario (8:30-18:30 Lun-Vie) - Hora Chile: {hora_chile}", flush=True)
        return
    
    ahora_chile = get_hora_chile()
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

def revisar_web_cada_1hora():
    """
    Revisa la web cada 1 hora (solo en horario)
    """
    if not en_horario():
        return
    
    ahora_chile = get_hora_chile()
    hora_str = get_hora_chile_str()
    print(f"🕐 [{hora_str}] ALERTA HORARIA - Verificando BDE...", flush=True)
    
    activa, mensaje = verificar_web()
    
    if activa:
        alerta = f"""
✅ *BDE: ONLINE* 🟢

🌐 Banco Central de Chile - SIETE
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora Chile: {hora_str}

✅ El sistema está funcionando correctamente.
"""
        enviar_alerta_telegram(alerta)
    else:
        alerta = f"""
🚨 *BDE: OFFLINE* 🔴

🌐 Banco Central de Chile - SIETE
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
👥 Destinatarios: Carl
⏱️ Revisión cada: 2 minutos
⏱️ Alerta horaria: Cada 1 hora
🕐 Horario: Lun-Vie 8:30-18:30 (hora Chile)
"""
    else:
        return f"""
📊 *ESTADO DEL MONITOR BDE*

❌ BDE: OFFLINE 🔴
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora Chile: {hora_chile}
📱 Alertas por: Telegram
👥 Destinatarios: Carl
⏱️ Revisión cada: 2 minutos
⏱️ Alerta horaria: Cada 1 hora
🕐 Horario: Lun-Vie 8:30-18:30 (hora Chile)
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

# ==================== SERVIDOR ====================

# Scheduler para revisión cada 2 minutos
scheduler_2min = BackgroundScheduler()
scheduler_2min.add_job(func=revisar_web_cada_2min, trigger="interval", minutes=2)
scheduler_2min.start()

# Scheduler para alerta horaria
scheduler_1hora = BackgroundScheduler()
scheduler_1hora.add_job(func=revisar_web_cada_1hora, trigger="interval", minutes=60)
scheduler_1hora.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("="*60)
    print("🚀 BDE MONITOR - Banco Central de Chile")
    print("="*60)
    print(f"📌 URL a monitorear: {URL_MONITOREO}")
    print(f"⏱️ Revisión cada: 2 minutos")
    print(f"⏱️ Alerta horaria: Cada 1 hora")
    print(f"📱 Alertas por: Telegram")
    print(f"🕐 Horario: Lun-Vie 8:30-18:30 (hora Chile)")
    print("="*60)
    app.run(host="0.0.0.0", port=port)
    
