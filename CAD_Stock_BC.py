def en_horario():
    """Verifica si estamos en horario de control (hora Chile)"""
    hora_chile = get_hora_chile()
    dia_semana = hora_chile.weekday()
    if dia_semana >= 5:
        return False
    hora = hora_chile.hour + hora_chile.minute / 60.0
    return 8.25 <= hora <= 18.75  # 8:15 AM a 6:45 PM (hora Chile)

def programar_alertas_horarias():
    """Programa alertas horarias fijas: 8:30, 9:30, 10:30...18:30"""
    horas = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    
    ahora = get_hora_chile()
    hoy = ahora.date()
    
    for hora in horas:
        hora_alerta = datetime(hoy.year, hoy.month, hoy.day, hora, 30, 0)
        
        if ahora >= hora_alerta:
            hora_alerta = hora_alerta + timedelta(days=1)
        
        scheduler_horaria.add_job(
            func=revisar_web_horaria,
            trigger="date",
            run_date=hora_alerta,
            args=[hora_alerta.strftime('%H:%M')]
        )
