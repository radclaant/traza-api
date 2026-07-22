"""Constantes de mapeo — copiadas tal cual del script de escritorio."""

BUSINESS_KEY = "secuencial"

HASH_COLUMNS: list[str] = []

DB_COLUMNS: set[str] = {
    "nro", "secuencial", "numero_envio_radicado", "identificacion", "paciente",
    "ingreso", "atencion", "tipo_cita", "unidad_funcional", "Cama", "estado_origen",
    "aseguradora", "aseguradora_contrato", "Tipo", "Sede", "sede_servicio",
    "id_servicio", "Servicio", "fecha_ingreso", "fecha_egreso", "alta_regente",
    "alta_facturador_dx", "alta_facturador_cx", "fecha_cierre", "fecha_envio",
    "fecha_envio_rips", "Regente", "FacturadorDx", "FacturadorCX", "usuario_cierra",
    "nom_usuario_cierra", "v_usuario_enviado", "nom_usuario_envia", "usuario_actual",
    "nom_usuario_actual", "nom_usuario_genera_rips", "Proceso", "documento_genera_rips",
    "ultimo_comentario", "total_sin_radicar", "hash_fila", "fecha_carga",
    "id_fecha_ingreso", "id_fecha_egreso", "status",
}

COLUMN_MAP: dict[str, str] = {
    "nro": "nro",
    "secuencial": "secuencial",
    "llave": "llave",
    "numero_envio_radicado": "numero_envio_radicado",
    "n_envio_radicado": "numero_envio_radicado",
    "no_envio_radicado": "numero_envio_radicado",
    "identificacion": "identificacion",
    "paciente": "paciente",
    "ingreso": "ingreso",
    "atencion": "atencion",
    "tipo_cita": "tipo_cita",
    "unidad_funcinal": "unidad_funcional",
    "cama": "Cama",
    "estado": "estado_origen",
    "estado_origen": "estado_origen",
    "aseguradora": "aseguradora",
    "aseguradora_contrato": "aseguradora_contrato",
    "tipo": "Tipo",
    "sede": "Sede",
    "sede_servicio": "sede_servicio",
    "id_servicio": "id_servicio",
    "servicio": "Servicio",
    "fecha_ingreso": "fecha_ingreso",
    "fecha_egreso": "fecha_egreso",
    "alta_regente": "alta_regente",
    "alta_facturador_dx": "alta_facturador_dx",
    "alta_facturador_cx": "alta_facturador_cx",
    "fecha_cierre": "fecha_cierre",
    "fecha_envio": "fecha_envio",
    "fecha_envio_rips": "fecha_envio_rips",
    "regente": "Regente",
    "facturador_dx": "FacturadorDx",
    "facturador_cx": "FacturadorCX",
    "usuario_cierre": "usuario_cierra",
    "usuario_cierra": "usuario_cierra",
    "nom_usuario_cierra": "nom_usuario_cierra",
    "v_usuario_envio": "v_usuario_enviado",
    "v_usuario_enviado": "v_usuario_enviado",
    "nom_usuario_envia": "nom_usuario_envia",
    "usuario_actual": "usuario_actual",
    "nom_usuario_actual": "nom_usuario_actual",
    "nom_usuario_genera_rips": "nom_usuario_genera_rips",
    "proceso": "Proceso",
    "documento_genera_rips": "documento_genera_rips",
    "ultimo_comentario": "ultimo_comentario",
    "total_sin_radicar": "total_sin_radicar",
}

TIMESTAMP_COLS = [
    "fecha_ingreso", "fecha_egreso", "alta_regente",
    "alta_facturador_dx", "alta_facturador_cx", "fecha_cierre",
    "fecha_envio", "fecha_envio_rips",
]
