def programar_alerta_horaria():
    """Programa la primera alerta 1 hora después del inicio, luego cada 1 hora"""
    ahora = get_hora_chile()
    hoy = ahora.date()
    
    # PRIMERA ALERTA: 1 hora después del inicio
    primera_alerta = ahora + timedelta(hours=1)
    
    # Verificar si cae dentro del horario de hoy
    hora = primera_alerta.hour + primera_alerta.minute / 60.0
    if 8.5 <= hora <= 18.75:
        print(f"⏰ Próxima alerta programada para HOY a las {primera_alerta.strftime('%H:%M')} (hora Chile)", flush=True)
    else:
        # Si no, programar para mañana a las 8:30
        primera_alerta = datetime(hoy.year, hoy.month, hoy.day, 8, 30, 0) + timedelta(days=1)
        print(f"⏰ Próxima alerta programada para MAÑANA a las {primera_alerta.strftime('%H:%M')} (hora Chile)", flush=True)
    
    # Programar la primera alerta
    scheduler_1hora.add_job(
        func=revisar_web_cada_1hora,
        trigger="date",
        run_date=primera_alerta
    )
    
    # Programar el resto cada 1 hora
    scheduler_1hora.add_job(
        func=revisar_web_cada_1hora,
        trigger="interval",
        hours=1,
        start_date=primera_alerta + timedelta(hours=1)
    )
