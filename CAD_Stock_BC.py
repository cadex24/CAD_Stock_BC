import os
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import time

app = Flask(__name__)

# ==================== CONFIGURACIÓN ====================

# IDs de Instagram
INSTAGRAM_IDS = {
    "bot": "27392412001",           # ID del bot
    "carl": "50637244",             # Tu ID
    "romina": "11789728112"         # ID de tu señora
}

# URL a monitorear
URL_MONITOREO = "https://si3.bcentral.cl/siete"

# Estado actual de la web
ESTADO_ACTUAL = "DESCONOCIDO"
ULTIMA_ALERTA_HORA = None

# ==================== FUNCIONES ====================

def enviar_alerta_instagram(mensaje):
    """
    Envía una alerta a Instagram (simulado por ahora)
    """
    print("="*60)
    print("📱 ALERTA INSTAGRAM")
    print("="*60)
    print(f"📌 Mensaje: {mensaje}")
    print(f"👥 Destinatarios:")
    print(f"   • Carl (ID: {INSTAGRAM_IDS['carl']})")
    print(f"   • Romina (ID: {INSTAGRAM_IDS['romina']})")
    print(f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print("")

def verificar_web():
    """
    Verifica el estado de la página web
    Retorna: (activa, mensaje)
    """
    global ESTADO_ACTUAL
    
    try:
        response = requests.get(URL_MONITOREO, timeout=10)
        if response.status_code == 200:
            ESTADO_ACTUAL = "ONLINE"
            return True, "✅ BDE: ONLINE 🟢"
        else:
            ESTADO_ACTUAL = "OFFLINE"
            return False, f"⚠️ BDE: OFFLINE 🔴 (Código: {response.status_code})"
    except requests.exceptions.Timeout:
        ESTADO_ACTUAL = "OFFLINE"
        return False, "❌ BDE: OFFLINE 🔴 (Timeout - No responde)"
    except requests.exceptions.ConnectionError:
        ESTADO_ACTUAL = "OFFLINE"
        return False, "❌ BDE: OFFLINE 🔴 (Error de conexión)"
    except Exception as e:
        ESTADO_ACTUAL = "OFFLINE"
        return False, f"❌ BDE: OFFLINE 🔴 (Error: {str(e)})"

def revisar_web_cada_2min():
    """
    Revisa la web cada 2 minutos para detectar caídas inmediatas
    """
    global ULTIMA_ALERTA_HORA, ESTADO_ACTUAL
    
    ahora = datetime.now()
    print(f"🕒 [{ahora.strftime('%H:%M:%S')}] Revisando BDE...", flush=True)
    
    activa, mensaje = verificar_web()
    print(f"   📊 {mensaje}", flush=True)
    
    # Si está OFFLINE, enviar alerta INMEDIATA
    if not activa:
        alerta = f"""
🚨 ALERTA INMEDIATA 🚨

🌐 BDE: OFFLINE 🔴

📌 URL: {URL_MONITOREO}
📊 Estado: {mensaje}
🕐 Hora: {ahora.strftime('%Y-%m-%d %H:%M:%S')}

⚠️ La página del Banco Central no está accesible.
"""
        enviar_alerta_instagram(alerta)
        ULTIMA_ALERTA_HORA = ahora

def revisar_web_cada_1hora():
    """
    Revisa la web cada 1 hora para confirmar que sigue online
    """
    global ULTIMO_ALERTA_HORA, ESTADO_ACTUAL
    
    ahora = datetime.now()
    print(f"🕐 [{ahora.strftime('%H:%M:%S')}] ALERTA HORARIA - Verificando BDE...", flush=True)
    
    activa, mensaje = verificar_web()
    
    if activa:
        # Enviar alerta de que sigue ONLINE
        alerta = f"""
✅ ESTADO BDE: ONLINE 🟢

🌐 Banco Central de Chile - SIETE
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora: {ahora.strftime('%Y-%m-%d %H:%M:%S')}

✅ El sistema sigue funcionando correctamente.
"""
        enviar_alerta_instagram(alerta)
        ULTIMA_ALERTA_HORA = ahora
    else:
        # Si está offline en la revisión horaria, enviar alerta inmediata
        alerta = f"""
🚨 ALERTA HORARIA 🚨

🌐 BDE: OFFLINE 🔴

📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Hora: {ahora.strftime('%Y-%m-%d %H:%M:%S')}

⚠️ La página del Banco Central no está accesible.
"""
        enviar_alerta_instagram(alerta)
        ULTIMA_ALERTA_HORA = ahora

def obtener_estado():
    """
    Comando para ver el estado actual
    """
    activa, mensaje = verificar_web()
    
    if activa:
        return f"""
📊 *ESTADO DEL MONITOR BDE*

✅ BDE: ONLINE 🟢
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Última revisión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👥 Destinatarios: Carl y Romina
⏱️ Revisión cada: 2 minutos
⏱️ Alerta horaria: Cada 1 hora
"""
    else:
        return f"""
📊 *ESTADO DEL MONITOR BDE*

❌ BDE: OFFLINE 🔴
📌 URL: {URL_MONITOREO}
📊 {mensaje}
🕐 Última revisión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👥 Destinatarios: Carl y Romina
⏱️ Revisión cada: 2 minutos
⏱️ Alerta horaria: Cada 1 hora
"""

# ==================== SERVIDOR ====================

# Scheduler para revisión cada 2 minutos
scheduler_2min = BackgroundScheduler()
scheduler_2min.add_job(func=revisar_web_cada_2min, trigger="interval", minutes=2)
scheduler_2min.start()

# Scheduler para alerta horaria
scheduler_1hora = BackgroundScheduler()
scheduler_1hora.add_job(func=revisar_web_cada_1hora, trigger="interval", minutes=60)
scheduler_1hora.start()

@app.route("/")
def index():
    return "🟢 BDE Monitor - Banco Central de Chile", 200

@app.route("/estado")
def estado():
    return obtener_estado()

@app.route("/test")
def test():
    """
    Endpoint para probar el envío de alertas
    """
    alerta = """
🧪 ALERTA DE PRUEBA

✅ Este es un mensaje de prueba del BDE Monitor.
🕐 Hora: {}
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    enviar_alerta_instagram(alerta)
    return "Alerta de prueba enviada", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("="*60)
    print("🚀 BDE MONITOR - Banco Central de Chile")
    print("="*60)
    print(f"📌 URL a monitorear: {URL_MONITOREO}")
    print(f"⏱️ Revisión cada: 2 minutos")
    print(f"⏱️ Alerta horaria: Cada 1 hora")
    print(f"👥 Destinatarios: Carl y Romina")
    print(f"🌐 Servidor en puerto: {port}")
    print("="*60)
    app.run(host="0.0.0.0", port=port)
