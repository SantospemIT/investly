import streamlit as st
from openai import OpenAI
import sqlite3
from fpdf import FPDF
import base64
from io import BytesIO
import re
import os

# Configuración inicial de la página DEBE SER LO PRIMERO   
st.set_page_config(
    page_title="Investly - Análisis de Inversión Inmobiliaria",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Configuración del cliente de OpenAI (versión segura)
client = None
if 'OPENAI_API_KEY' in st.secrets:
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        st.session_state['openai_configured'] = True
    except Exception as e:
        st.error(f"Error al configurar OpenAI: {str(e)}")
        st.session_state['openai_configured'] = False
else:
    st.warning("Funcionalidad de IA limitada - No se configuró OPENAI_API_KEY")
    st.session_state['openai_configured'] = False

# Estilos CSS personalizados para Investly
def load_css():
    st.markdown("""
    <style>
        :root {
            --azul-oscuro: #1E3A8A;
            --azul-medio: #2563EB;
            --azul-claro: #3B82F6;
            --gris: #6B7280;
            --blanco: #FFFFFF;
            --verde: #10B981;
            --rojo: #EF4444;
        }
        
        .stApp {
            max-width: 900px;
            margin: auto;
            font-family: 'Inter', 'Arial', sans-serif;
            background-color: #F9FAFB;
        }
        
        .header-container {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            justify-content: center;
            text-align: center;
        }
        
        .logo {
            height: 70px;
            margin-right: 15px;
        }
        
        .calculator-container {
            background-color: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin-bottom: 25px;
            border: 1px solid #E5E7EB;
        }
        
        .stButton>button {
            background-color: var(--azul-medio);
            color: white;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 600;
            width: 100%;
            border: none;
            transition: background-color 0.3s;
        }
        
        .stButton>button:hover {
            background-color: var(--azul-oscuro);
            color: white;
        }
        
        .stTextInput>div>div>input, 
        .stNumberInput>div>div>input,
        .stSelectbox>div>div>select,
        .stMultiselect>div>div>div {
            border-radius: 8px;
            border: 1px solid #D1D5DB;
            padding: 10px;
        }
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: var(--azul-oscuro);
        }
        
        .stMetric {
            border-left: 4px solid var(--azul-medio);
            padding-left: 15px;
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .positive-value {
            color: var(--verde);
            font-weight: bold;
        }
        
        .negative-value {
            color: var(--rojo);
            font-weight: bold;
        }
        
        .data-table {
            width: 100%;
            margin-bottom: 20px;
            border-collapse: collapse;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .data-table th {
            background-color: var(--azul-medio);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        
        .data-table td {
            border: 1px solid #E5E7EB;
            padding: 10px;
            text-align: left;
        }
        
        .data-table tr:nth-child(even) {
            background-color: #F9FAFB;
        }
        
        .data-table input {
            width: 100%;
            padding: 8px;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
        }
        
        .data-table .total-row {
            background-color: #EFF6FF;
            font-weight: bold;
        }
        
        .tips-container {
            background-color: #f0f9ff;
            border-left: 4px solid var(--azul-medio);
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 0 8px 8px 0;
        }
        
        .help-icon {
            color: var(--azul-medio);
            cursor: pointer;
            margin-left: 5px;
            font-weight: bold;
        }
        
        .help-text {
            display: none;
            position: absolute;
            background-color: white;
            border: 1px solid var(--gris);
            padding: 12px;
            border-radius: 8px;
            z-index: 100;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            width: 300px;
            font-size: 14px;
        }
        
        .help-icon:hover + .help-text {
            display: block;
        }
        
        .tagline {
            color: var(--gris);
            font-style: italic;
            margin-top: 5px;
            font-size: 16px;
        }
        
        .investment-card {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid var(--azul-medio);
        }
        
        @media (max-width: 768px) {
            .header-container {
                flex-direction: column;
                text-align: center;
            }
            
            .logo {
                margin-right: 0;
                margin-bottom: 15px;
            }
            
            .help-text {
                width: 200px;
                font-size: 12px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# Función para formatear números como moneda
def format_currency(value):
    return f"${value:,.2f}" if value else "$0.00"

# Función para extraer el valor numérico de un string de moneda
def parse_currency(currency_str):
    if not currency_str:
        return 0.0
    # Eliminar símbolos de moneda y comas
    num_str = re.sub(r'[^\d.]', '', currency_str)
    return float(num_str) if num_str else 0.0

# Función para generar PDF
def generate_pdf(usuario_data, finanzas_data, analisis_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Investly - Informe de Análisis Financiero", ln=1, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Evaluación de Inversión en Bienes Raíces", ln=1, align='C')
    pdf.ln(10)
    
    # Datos personales
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Datos Personales:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Nombre: {usuario_data.get('nombre', '')}", ln=1)
    pdf.cell(200, 10, txt=f"Edad: {usuario_data.get('edad', '')}", ln=1)
    pdf.cell(200, 10, txt=f"Email: {usuario_data.get('email', '')}", ln=1)
    pdf.ln(5)
    
    # Datos financieros
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Situación Financiera:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Ingresos Mensuales: {format_currency(finanzas_data.get('ingresos', 0))}", ln=1)
    pdf.cell(200, 10, txt=f"Gastos Mensuales: {format_currency(finanzas_data.get('gastos', 0))}", ln=1)
    pdf.cell(200, 10, txt=f"Activos Totales: {format_currency(finanzas_data.get('activos', 0))}", ln=1)
    pdf.cell(200, 10, txt=f"Pasivos Totales: {format_currency(finanzas_data.get('pasivos', 0))}", ln=1)
    pdf.ln(5)
    
    # Perfil de inversión
    if 'perfil_inversion' in analisis_data:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=f"Perfil de Inversión en Bienes Raíces: {analisis_data['perfil_inversion']['nivel']}", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=analisis_data['perfil_inversion']['descripcion'])
        pdf.ln(5)
    
    # Análisis
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Análisis y Recomendaciones:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=analisis_data.get('resumen', ''))
    pdf.ln(5)
    
    # Plan de trabajo
    if 'plan_trabajo' in analisis_data:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="Plan de Trabajo Personalizado:", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=analisis_data['plan_trabajo'])
    
    # Recomendaciones de cursos
    if 'recomendaciones_cursos' in analisis_data:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="Recomendaciones de Educación Financiera:", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=analisis_data['recomendaciones_cursos'])
    
    # Generar el PDF en memoria
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_bytes = pdf_output.getvalue()
    pdf_output.close()
    
    return pdf_bytes

# Crear la base de datos y la tabla de usuarios
def crear_base_datos():
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            edad INTEGER,
            email TEXT,
            telefono TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finanzas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            ingresos_mensuales REAL,
            gastos_mensuales REAL,
            activos_totales REAL,
            pasivos_totales REAL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()

# Registrar un nuevo usuario
def registrar_usuario(nombre, edad, email, telefono):
    if edad < 18:
        st.warning("Debes ser mayor de 18 años para usar este programa.")
        return None
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO usuarios (nombre, edad, email, telefono)
        VALUES (?, ?, ?, ?)
    ''', (nombre, edad, email, telefono))
    usuario_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return usuario_id

# Función para analizar la proyección de retiro con enfoque en bienes raíces
def analizar_proyeccion_retiro(edad_actual, edad_retiro, ingresos_retiro, gastos_retiro, ahorros_retiro, patrimonio_neto, flujo_caja):
    años_ahorro = edad_retiro - edad_actual
    necesidad_total = (ingresos_retiro - gastos_retiro) * (100 - edad_retiro)  # Estimación simplificada
    ahorro_necesario_anual = (necesidad_total - ahorros_retiro) / años_ahorro if años_ahorro > 0 else 0
    
    # Análisis específico para bienes raíces
    recomendaciones = []
    cursos_recomendados = []
    
    if patrimonio_neto > 50000 and flujo_caja > 1000:
        nivel = "Alto"
        recomendaciones.append("Tienes un excelente perfil para comenzar a invertir en bienes raíces de inmediato.")
        recomendaciones.append("Considera propiedades generadoras de ingresos pasivos como apartamentos en arriendo o locales comerciales.")
        cursos_recomendados.append("Curso Avanzado de Inversión en Bienes Raíces")
    elif patrimonio_neto > 20000 and flujo_caja > 500:
        nivel = "Medio"
        recomendaciones.append("Tienes potencial para inversión en bienes raíces, pero necesitas mejorar tu flujo de caja.")
        recomendaciones.append("Considera comenzar con propiedades pequeñas o co-inversiones.")
        cursos_recomendados.append("Curso Intermedio de Bienes Raíces")
    else:
        nivel = "Bajo"
        recomendaciones.append("Necesitas fortalecer tu situación financiera antes de invertir en bienes raíces.")
        recomendaciones.append("Enfócate en aumentar tus ingresos y reducir deudas.")
        cursos_recomendados.append("Curso Básico de Educación Financiera para Bienes Raíces")
    
    recomendaciones.append("\nTe recomendamos estos recursos educativos:")
    recomendaciones.append("- Portal Educativo de Investly: https://investly.com/cursos")
    recomendaciones.append("- Blog de Estrategias Inmobiliarias: https://investly.com/blog")
    
    return {
        "años_ahorro": años_ahorro,
        "necesidad_total": necesidad_total,
        "ahorro_necesario_anual": ahorro_necesario_anual,
        "nivel_inversion": nivel,
        "analisis": f"""
        Proyección de Retiro con Enfoque en Bienes Raíces:
        - Años hasta el retiro: {años_ahorro}
        - Necesidad total estimada: {format_currency(necesidad_total)}
        - Ahorros actuales: {format_currency(ahorros_retiro)}
        - Necesitas ahorrar aproximadamente {format_currency(ahorro_necesario_anual)} anuales para alcanzar tu meta.
        
        Perfil de Inversión: {nivel}
        
        Recomendaciones Específicas:
        {chr(10).join(recomendaciones)}
        
        Cursos Recomendados:
        {chr(10).join(cursos_recomendados)}
        """
    }

# Calcular y mostrar el análisis financiero con enfoque en bienes raíces
def analizar_situacion_financiera(ingresos, gastos, activos, pasivos):
    flujo_caja_mensual = ingresos - gastos
    patrimonio_neto = activos - pasivos
    
    # Determinar perfil de inversión en bienes raíces
    if patrimonio_neto > 50000 and flujo_caja_mensual > 1000:
        perfil = "Alto (70-100%)"
        descripcion = "Excelente perfil para inversión en bienes raíces. Tienes la capacidad financiera para comenzar a invertir en propiedades generadoras de ingresos pasivos."
    elif patrimonio_neto > 20000 and flujo_caja_mensual > 500:
        perfil = "Medio (40-69%)"
        descripcion = "Buen potencial para inversión en bienes raíces. Considera comenzar con propiedades pequeñas o co-inversiones mientras mejoras tu flujo de caja."
    else:
        perfil = "Bajo (0-39%)"
        descripcion = "Necesitas fortalecer tu situación financiera antes de invertir en bienes raíces. Enfócate en aumentar ingresos, reducir deudas y ahorrar."
    
    st.subheader("📊 Análisis Resumen de tu Situación Financiera")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Ingresos Mensuales", format_currency(ingresos))
        st.metric("Gastos Mensuales", format_currency(gastos))
        st.metric("Flujo de Caja Mensual", format_currency(flujo_caja_mensual), 
                 delta="Positivo" if flujo_caja_mensual > 0 else "Negativo",
                 delta_color="normal" if flujo_caja_mensual > 0 else "inverse")
    
    with col2:
        st.metric("Activos Totales", format_currency(activos))
        st.metric("Pasivos Totales", format_currency(pasivos))
        st.metric("Patrimonio Neto", format_currency(patrimonio_neto), 
                 delta="Positivo" if patrimonio_neto > 0 else "Negativo",
                 delta_color="normal" if patrimonio_neto > 0 else "inverse")
    
    st.subheader("🏡 Perfil de Inversión en Bienes Raíces")
    st.markdown(f"""
    <div class="calculator-container">
        <h4>Nivel: {perfil}</h4>
        <p>{descripcion}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("🔍 Análisis Específico para Bienes Raíces")
    if flujo_caja_mensual > 0:
        st.success(f"Flujo de caja positivo de {format_currency(flujo_caja_mensual)}/mes. Podrías destinar parte de este excedente a inversión en propiedades.")
    else:
        st.error(f"Flujo de caja negativo de {format_currency(flujo_caja_mensual)}/mes. Necesitas equilibrar tus finanzas antes de considerar inversiones.")
    
    if patrimonio_neto > 50000:
        st.success("Patrimonio neto sólido. Podrías usar parte como garantía para financiamiento de propiedades.")
    elif patrimonio_neto > 0:
        st.warning("Patrimonio neto positivo pero modesto. Considera estrategias de bajo riesgo como alquiler de habitaciones.")
    else:
        st.error("Patrimonio neto negativo. Enfócate en reducir deudas antes de invertir.")
    
    st.subheader("🚀 Acciones Recomendadas para Bienes Raíces")
    st.write("""
    1. **Analiza tu capacidad de endeudamiento** para financiamiento hipotecario
    2. **Explora opciones de co-inversión** si tu capital es limitado
    3. **Considera propiedades con múltiples fuentes de ingreso** (alquiler, parking, lavandería)
    4. **Estudia el mercado local** para identificar oportunidades
    5. **Consulta nuestros recursos educativos** para aprender estrategias específicas
    """)
    
    return {
        "flujo_caja": flujo_caja_mensual,
        "patrimonio": patrimonio_neto,
        "perfil_inversion": {
            "nivel": perfil,
            "descripcion": descripcion
        },
        "resumen": f"""
        Situación Financiera Actual:
        - Ingresos Mensuales: {format_currency(ingresos)}
        - Gastos Mensuales: {format_currency(gastos)}
        - Flujo de Caja: {format_currency(flujo_caja_mensual)} ({'Positivo' if flujo_caja_mensual > 0 else 'Negativo'})
        - Activos Totales: {format_currency(activos)}
        - Pasivos Totales: {format_currency(pasivos)}
        - Patrimonio Neto: {format_currency(patrimonio_neto)} ({'Positivo' if patrimonio_neto > 0 else 'Negativo'})
        
        Perfil de Inversión en Bienes Raíces: {perfil}
        {descripcion}
        
        Análisis:
        {'Tienes un flujo de caja positivo que podrías destinar a inversión en propiedades.' if flujo_caja_mensual > 0 else 'Necesitas equilibrar tu flujo de caja antes de considerar inversiones.'}
        {'Tu patrimonio neto es sólido y podrías usarlo como garantía para financiamiento.' if patrimonio_neto > 50000 else 'Considera fortalecer tu patrimonio antes de inversiones significativas.'}
        """
    }

# Generar plan de trabajo financiero con enfoque en bienes raíces
def generar_plan_trabajo(ingresos, gastos, activos, pasivos):
    if not st.session_state.get('openai_configured', False):
        return "Servicio de IA no disponible en este momento. Por favor configura tu clave de OpenAI API en secrets.toml para habilitar esta función."
    
    prompt = f"""
    Como experto en bienes raíces y finanzas personales, analiza esta situación financiera:
    - Ingresos: {format_currency(ingresos)}/mes
    - Gastos: {format_currency(gastos)}/mes
    - Activos: {format_currency(activos)}
    - Pasivos: {format_currency(pasivos)}
    
    Crea un plan detallado orientado específicamente a inversión en bienes raíces que incluya:
    1. Diagnóstico claro de la situación actual con enfoque en bienes raíces
    2. Estrategias para mejorar el flujo de caja aplicables a inversión inmobiliaria
    3. Plan de reducción de deudas que permita acceder a financiamiento hipotecario
    4. Recomendaciones de inversión en bienes raíces personalizadas según el perfil
    5. Metas a corto (3 meses), mediano (1 año) y largo plazo (5+ años) para construir patrimonio inmobiliario
    6. Ejercicios prácticos para identificar oportunidades locales
    7. Recomendaciones específicas de cursos y recursos educativos
    
    Usa un lenguaje claro y motivador, con ejemplos concretos de estrategias inmobiliarias.
    Respuesta en español.
    """
    
    try:
        with st.spinner('Generando tu plan personalizado para bienes raíces...'):
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asesor experto en inversión en bienes raíces. Responde en español con enfoque práctico para inversión inmobiliaria."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error al generar el plan: {str(e)}")
        return "No se pudo generar el plan en este momento."

# Función para crear tooltip de ayuda
def help_tooltip(text):
    st.markdown(f"""
    <span class="help-icon">?
        <span class="help-text">{text}</span>
    </span>
    """, unsafe_allow_html=True)

# Interfaz principal de Streamlit
def main():
    load_css()  # Cargar estilos CSS personalizados
    
    # Encabezado con logo
    st.markdown("""
    <div class="header-container">
        <div>
            <h1 style="margin:0;color:#1E3A8A;">Investly</h1>
            <p class="tagline">Tu perfil. Tu estrategia. Tu patrimonio.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="calculator-container">
        Esta herramienta te ayudará a analizar tu capacidad para invertir en bienes raíces, 
        crear un plan de acción y establecer metas claras para construir patrimonio inmobiliario.
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializar variables de sesión para el reporte
    if 'reporte_data' not in st.session_state:
        st.session_state['reporte_data'] = {
            'usuario': {},
            'finanzas': {},
            'analisis': {}
        }
    
    # Paso 1: Registro de usuario
    with st.container():
        st.subheader("📝 Información Personal")
        nombre = st.text_input("Nombre completo")
        edad = st.number_input("Edad", min_value=18, max_value=100, value=30)
        email = st.text_input("Email")
        telefono = st.text_input("Teléfono")
        
        if st.button("Guardar información personal"):
            if nombre and email:
                usuario_id = registrar_usuario(nombre, edad, email, telefono)
                st.session_state['usuario_id'] = usuario_id
                st.session_state['reporte_data']['usuario'] = {
                    'nombre': nombre,
                    'edad': edad,
                    'email': email,
                    'telefono': telefono
                }
                st.success("Información guardada correctamente")
            else:
                st.warning("Por favor completa todos los campos obligatorios")
    
    # Paso 2: Datos financieros - Activos y Pasivos
    if 'usuario_id' in st.session_state:
        with st.container():
            st.subheader("📊 Elaborar mi presupuesto")
            st.markdown("""
            **Ejercicio:** Comienza por hacer un presupuesto detallado de tu gasto diario y mensual. 
            Revisa extractos de cuentas y tarjetas, y anota todo lo que gastas en efectivo. 
            Identifica oportunidades para destinar recursos a inversión en bienes raíces.
            """)
            
            st.subheader("💰 Activos y Pasivos")
            
            # Lista de activos y pasivos con tooltips
            activos_items = [
                {"nombre": "Inmueble 1", "help": "Valor de mercado de tu primera propiedad (casa, apartamento, terreno)"},
                {"nombre": "Inmueble 2", "help": "Valor de mercado de tu segunda propiedad (si aplica)"},
                {"nombre": "Automóvil 1", "help": "Valor actual de tu vehículo principal"},
                {"nombre": "Automóvil 2", "help": "Valor actual de tu segundo vehículo (si aplica)"},
                {"nombre": "Muebles", "help": "Valor estimado de muebles y enseres"},
                {"nombre": "Joyas", "help": "Valor estimado de joyas y artículos de valor"},
                {"nombre": "Arte", "help": "Valor estimado de obras de arte y colecciones"},
                {"nombre": "Efectivo cuenta 1", "help": "Saldo disponible en tu cuenta principal"},
                {"nombre": "Efectivo cuenta 2", "help": "Saldo disponible en cuentas secundarias"},
                {"nombre": "Deudas por cobrar", "help": "Dinero que te deben otras personas o empresas"},
                {"nombre": "Bonos o títulos valores", "help": "Valor de tus inversiones financieras"},
                {"nombre": "Fondo de retiro", "help": "Saldo acumulado en fondos de pensiones"},
                {"nombre": "Bonos o derechos laborales", "help": "Valor de prestaciones laborales"}
            ]
            
            pasivos_items = [
                {"nombre": "Tarjeta de crédito 1", "help": "Saldo pendiente en tu tarjeta principal"},
                {"nombre": "Tarjeta de crédito 2", "help": "Saldo pendiente en tarjetas secundarias"},
                {"nombre": "Tarjeta de crédito 3", "help": "Otras deudas con tarjetas de crédito"},
                {"nombre": "Otra deuda 1", "help": "Préstamos personales o de consumo"},
                {"nombre": "Otra deuda 2", "help": "Préstamos estudiantiles o educativos"},
                {"nombre": "Otra deuda 3", "help": "Otras obligaciones financieras"},
                {"nombre": "Otros", "help": "Cualquier otra deuda no clasificada"}
            ]
            
            # Inicializar valores en session_state si no existen
            if 'activos_values' not in st.session_state:
                st.session_state['activos_values'] = {item['nombre']: {"valor": 0.0, "deuda": 0.0} for item in activos_items}
            
            if 'pasivos_values' not in st.session_state:
                st.session_state['pasivos_values'] = {item['nombre']: {"valor": 0.0, "deuda": 0.0} for item in pasivos_items}
            
            # Tabla de activos
            st.markdown("<h4>Activos</h4>", unsafe_allow_html=True)
            
            # Encabezados de tabla
            cols = st.columns([3, 1, 1, 1])
            cols[0].markdown("<b>Descripción</b>", unsafe_allow_html=True)
            cols[1].markdown("<b>Valor ($)</b>", unsafe_allow_html=True)
            cols[2].markdown("<b>Deuda ($)</b>", unsafe_allow_html=True)
            cols[3].markdown("<b>Activo Neto ($)</b>", unsafe_allow_html=True)
            
            activos_total = {"valor": 0.0, "deuda": 0.0, "neto": 0.0}
            
            for item in activos_items:
                cols = st.columns([3, 1, 1, 1])
                
                # Descripción con tooltip
                with cols[0]:
                    st.markdown(f"{item['nombre']} <span class='help-icon'>?<span class='help-text'>{item['help']}</span></span>", unsafe_allow_html=True)
                
                # Campos de valor y deuda
                valor = cols[1].text_input(
                    f"Valor {item['nombre']}",
                    value=format_currency(st.session_state['activos_values'][item['nombre']]['valor']),
                    key=f"activo_valor_{item['nombre']}",
                    label_visibility="collapsed"
                )
                
                deuda = cols[2].text_input(
                    f"Deuda {item['nombre']}",
                    value=format_currency(st.session_state['activos_values'][item['nombre']]['deuda']),
                    key=f"activo_deuda_{item['nombre']}",
                    label_visibility="collapsed"
                )
                
                # Calcular activo neto
                valor_parsed = parse_currency(valor)
                deuda_parsed = parse_currency(deuda)
                neto = valor_parsed - deuda_parsed
                
                # Mostrar activo neto
                cols[3].markdown(f"<div style='padding: 0.5rem;'>{format_currency(neto)}</div>", unsafe_allow_html=True)
                
                # Actualizar session state y totales
                st.session_state['activos_values'][item['nombre']] = {
                    "valor": valor_parsed,
                    "deuda": deuda_parsed
                }
                
                activos_total["valor"] += valor_parsed
                activos_total["deuda"] += deuda_parsed
                activos_total["neto"] += neto
            
            # Tabla de pasivos
            st.markdown("<h4>Pasivos</h4>", unsafe_allow_html=True)
            
            # Encabezados de tabla
            cols = st.columns([3, 1, 1, 1])
            cols[0].markdown("<b>Descripción</b>", unsafe_allow_html=True)
            cols[1].markdown("<b>Valor ($)</b>", unsafe_allow_html=True)
            cols[2].markdown("<b>Deuda ($)</b>", unsafe_allow_html=True)
            cols[3].markdown("<b>Activo Neto ($)</b>", unsafe_allow_html=True)
            
            pasivos_total = {"valor": 0.0, "deuda": 0.0, "neto": 0.0}
            
            for item in pasivos_items:
                cols = st.columns([3, 1, 1, 1])
                
                # Descripción con tooltip
                with cols[0]:
                    st.markdown(f"{item['nombre']} <span class='help-icon'>?<span class='help-text'>{item['help']}</span></span>", unsafe_allow_html=True)
                
                # Campos de valor y deuda (para pasivos, valor es el monto total de la deuda)
                valor = cols[1].text_input(
                    f"Valor {item['nombre']}",
                    value=format_currency(st.session_state['pasivos_values'][item['nombre']]['valor']),
                    key=f"pasivo_valor_{item['nombre']}",
                    label_visibility="collapsed"
                )
                
                # Para pasivos, la "deuda" sería el saldo pendiente (podría ser igual al valor)
                deuda = cols[2].text_input(
                    f"Deuda {item['nombre']}",
                    value=format_currency(st.session_state['pasivos_values'][item['nombre']]['deuda']),
                    key=f"pasivo_deuda_{item['nombre']}",
                    label_visibility="collapsed"
                )
                
                # Calcular activo neto (para pasivos sería negativo)
                valor_parsed = parse_currency(valor)
                deuda_parsed = parse_currency(deuda)
                neto = -(valor_parsed - deuda_parsed)  # Negativo porque son pasivos
                
                # Mostrar activo neto
                cols[3].markdown(f"<div style='padding: 0.5rem;'>{format_currency(neto)}</div>", unsafe_allow_html=True)
                
                # Actualizar session state y totales
                st.session_state['pasivos_values'][item['nombre']] = {
                    "valor": valor_parsed,
                    "deuda": deuda_parsed
                }
                
                pasivos_total["valor"] += valor_parsed
                pasivos_total["deuda"] += deuda_parsed
                pasivos_total["neto"] += neto
            
            # Mostrar totales
            st.markdown(f"""
            <div class="calculator-container">
                <h4>Totales</h4>
                <table style="width:100%">
                    <tr>
                        <td><strong>Total Valor Activos:</strong></td>
                        <td>{format_currency(activos_total['valor'])}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Deuda Activos:</strong></td>
                        <td>{format_currency(activos_total['deuda'])}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Activos Netos:</strong></td>
                        <td>{format_currency(activos_total['neto'])}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Pasivos:</strong></td>
                        <td>{format_currency(pasivos_total['neto'])}</td>
                    </tr>
                    <tr style="font-weight:bold; background-color:#EFF6FF;">
                        <td><strong>Patrimonio Neto:</strong></td>
                        <td>{format_currency(activos_total['neto'] + pasivos_total['neto'])}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            # Flujo de caja mensual
            st.subheader("💸 Flujo de Caja Mensual")
            
            with st.expander("ℹ️ ¿Qué es el flujo de caja?"):
                st.markdown("""
                El flujo de caja es la diferencia entre tus ingresos y gastos mensuales. 
                Un flujo positivo significa que tienes dinero disponible para ahorrar o invertir, 
                mientras que un flujo negativo indica que gastas más de lo que ganas.
                
                Para inversión en bienes raíces, un flujo de caja positivo es esencial, ya que:
                - Te permite ahorrar para la cuota inicial de una propiedad
                - Demuestra capacidad de pago para obtener financiamiento
                - Puede usarse para cubrir gastos de propiedades en arriendo
                """)
            
            # Inicializar valores en session_state si no existen
            if 'ingresos_values' not in st.session_state:
                st.session_state['ingresos_values'] = {
                    "Ingresos mensuales adulto 1": {"valor": 0.0, "help": "Salario, honorarios o ingresos principales del primer adulto en el hogar"},
                    "Ingresos mensuales adulto 2": {"valor": 0.0, "help": "Salario, honorarios o ingresos principales del segundo adulto en el hogar (si aplica)"},
                    "Otros ingresos": {"valor": 0.0, "help": "Ingresos adicionales como arriendos, inversiones, negocios secundarios"}
                }
            
            if 'gastos_values' not in st.session_state:
                st.session_state['gastos_values'] = {
                    "Gasto de Inmueble 1": {"valor": 0.0, "help": "Hipoteca, administración, impuestos y mantenimiento de tu vivienda principal"},
                    "Gasto de Inmueble 2": {"valor": 0.0, "help": "Hipoteca, administración, impuestos y mantenimiento de tu segunda propiedad (si aplica)"},
                    "Alimentación": {"valor": 0.0, "help": "Supermercado, restaurantes y gastos de comida en general"},
                    "Educación": {"valor": 0.0, "help": "Colegiatura, universidad, cursos y materiales educativos"},
                    "Transporte": {"valor": 0.0, "help": "Gasolina, transporte público, mantenimiento vehicular"},
                    "Salud": {"valor": 0.0, "help": "Seguros médicos, medicinas, consultas"},
                    "Entretenimiento": {"valor": 0.0, "help": "Salidas, viajes, suscripciones (Netflix, etc.)"},
                    "Servicios públicos": {"valor": 0.0, "help": "Agua, luz, gas, internet, teléfono"},
                    "Seguros": {"valor": 0.0, "help": "Seguro de vida, vehicular, hogar"},
                    "Otros gastos": {"valor": 0.0, "help": "Cualquier otro gasto no clasificado"}
                }
            
            # Ingresos
            st.markdown("<h4>Ingresos</h4>", unsafe_allow_html=True)
            ingresos_total = 0.0
            
            for item, data in st.session_state['ingresos_values'].items():
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"{item} <span class='help-icon'>?<span class='help-text'>{data['help']}</span></span>", unsafe_allow_html=True)
                
                value = cols[1].text_input(
                    f"{item} ($)",
                    value=format_currency(data['valor']),
                    key=f"ingreso_{item}",
                    label_visibility="collapsed"
                )
                parsed_value = parse_currency(value)
                st.session_state['ingresos_values'][item]['valor'] = parsed_value
                ingresos_total += parsed_value
            
            # Gastos
            st.markdown("<h4>Gastos</h4>", unsafe_allow_html=True)
            gastos_total = 0.0
            
            for item, data in st.session_state['gastos_values'].items():
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"{item} <span class='help-icon'>?<span class='help-text'>{data['help']}</span></span>", unsafe_allow_html=True)
                
                value = cols[1].text_input(
                    f"{item} ($)",
                    value=format_currency(data['valor']),
                    key=f"gasto_{item}",
                    label_visibility="collapsed"
                )
                parsed_value = parse_currency(value)
                st.session_state['gastos_values'][item]['valor'] = parsed_value
                gastos_total += parsed_value
            
            # Calcular saldo mensual
            saldo_mensual = ingresos_total - gastos_total
            
            # Mostrar resumen de flujo de caja
            st.markdown(f"""
            <div class="calculator-container">
                <h4>Resumen Flujo de Caja</h4>
                <table style="width:100%">
                    <tr>
                        <td><strong>Total Ingresos:</strong></td>
                        <td class="positive-value">{format_currency(ingresos_total)}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Gastos:</strong></td>
                        <td class="negative-value">{format_currency(gastos_total)}</td>
                    </tr>
                    <tr style="font-weight:bold; background-color:#EFF6FF;">
                        <td><strong>Saldo Mensual:</strong></td>
                        <td class="{ 'positive-value' if saldo_mensual >= 0 else 'negative-value' }">{format_currency(saldo_mensual)}</td>
                    </tr>
                </table>
                
                <p style="margin-top:10px;">
                    {f"💡 Tienes {format_currency(saldo_mensual)} disponibles cada mes para ahorrar o invertir en bienes raíces." if saldo_mensual > 0 else 
                      f"⚠️ Estás gastando {format_currency(abs(saldo_mensual))} más de lo que ganas cada mes. Considera ajustar tus gastos."}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Analizar mi situación financiera para bienes raíces"):
                # Calcular total de activos netos (suma de activos netos + pasivos netos)
                total_activos_netos = activos_total['neto'] + pasivos_total['neto']
                
                st.session_state['datos_financieros'] = (ingresos_total, gastos_total, total_activos_netos, abs(pasivos_total['neto']))
                analisis = analizar_situacion_financiera(ingresos_total, gastos_total, total_activos_netos, abs(pasivos_total['neto']))
                st.session_state['reporte_data']['finanzas'] = {
                    'ingresos': ingresos_total,
                    'gastos': gastos_total,
                    'activos': total_activos_netos,
                    'pasivos': abs(pasivos_total['neto'])
                }
                st.session_state['reporte_data']['analisis']['resumen'] = analisis['resumen']
                st.session_state['reporte_data']['analisis']['perfil_inversion'] = analisis['perfil_inversion']
                
                # Generar y mostrar plan de trabajo específico para bienes raíces
                plan = generar_plan_trabajo(ingresos_total, gastos_total, total_activos_netos, abs(pasivos_total['neto']))
                st.subheader("📝 Plan de Trabajo para Inversión en Bienes Raíces")
                st.write(plan)
                st.session_state['reporte_data']['analisis']['plan_trabajo'] = plan
                
                # Recomendaciones de cursos según perfil
                if analisis['perfil_inversion']['nivel'].startswith("Alto"):
                    cursos = """
                    Recomendaciones de Cursos:
                    - Curso Avanzado de Estrategias Inmobiliarias
                    - Taller de Financiamiento Creativo para Propiedades
                    - Masterclass en Identificación de Oportunidades
                    """
                elif analisis['perfil_inversion']['nivel'].startswith("Medio"):
                    cursos = """
                    Recomendaciones de Cursos:
                    - Curso Intermedio de Inversión en Bienes Raíces
                    - Taller de Co-Inversiones y Sociedades
                    - Seminario de Análisis de Mercado Local
                    """
                else:
                    cursos = """
                    Recomendaciones de Cursos:
                    - Curso Básico de Educación Financiera
                    - Taller de Presupuesto and Ahorro
                    - Introducción a la Inversión en Bienes Raíces
                    """
                
                st.session_state['reporte_data']['analisis']['recomendaciones_cursos'] = cursos
                
                # Mostrar recursos adicionales
                st.subheader("🎓 Recursos Educativos Recomendados")
                st.markdown("""
                - [Portal Educativo de Investly](https://investly.com/cursos)
                - [Blog de Estrategias Inmobiliarias](https://investly.com/blog)
                - [Guía de Inversión para Principiantes](https://investly.com/guias)
                - [Webinars Gratuitos](https://investly.com/webinars)
                """)
    
    # Paso 3: Plan de inversión en bienes raíces
    if 'datos_financieros' in st.session_state:
        with st.container():
            st.subheader("📈 Plan de Inversión en Bienes Raíces")
            
            # Sección de tips como habladores
            with st.expander("💡 ESTRATEGIAS PARA INVERTIR EN BIENES RAÍCES"):
                st.markdown("""
                <div class="tips-container">
                    **1. Propiedades en Remate Bancario**  
                    Los bancos suelen vender propiedades embargadas por debajo del valor de mercado. Requiere investigación pero puede ofrecer excelentes oportunidades.
                    
                    **2. Compra con Opción de Compra**  
                    Negocia con el propietario el derecho a comprar la propiedad en el futuro a un precio acordado, mientras la alquilas.
                    
                    **3. Co-Inversiones**  
                    Asóciate con otros inversionistas para adquirir propiedades que individualmente no podrías comprar.
                    
                    **4. Propiedades con Dueño Directo**  
                    Muchas veces puedes encontrar mejores negocios tratando directamente con dueños que no usan agentes inmobiliarios.
                    
                    **5. Rehabilitación de Propiedades**  
                    Compra propiedades que necesiten reparaciones, haz mejoras estratégicas y véndelas con ganancia o alquílalas por mayor valor.
                    
                    **6. Rentas por Habitación**  
                    En lugar de alquilar una propiedad completa, alquila por habitaciones para maximizar el ingreso.
                    
                    **7. Propiedades Comerciales**  
                    Locales comerciales pueden ofrecer mayores rentabilidades que propiedades residenciales.
                    
                    **8. Terrenos con Potencial**  
                    Identifica terrenos en zonas con crecimiento futuro y adquiérelos antes de que suban de valor.
                    
                    **9. Propiedades con Múltiples Fuentes de Ingreso**  
                    Busca propiedades que permitan generar ingresos adicionales (lavandería, parqueaderos, etc.).
                    
                    **10. Rentas Vacacionales**  
                    Propiedades en zonas turísticas pueden generar ingresos significativos por rentas a corto plazo.
                </div>
                """, unsafe_allow_html=True)
            
            objetivos = st.text_input("Objetivos específicos con bienes raíces", 
                                    "Generar ingresos pasivos a través de propiedades en alquiler")
            horizonte = st.selectbox("Horizonte de inversión", 
                                   ["Corto plazo (1-3 años)", "Mediano plazo (3-5 años)", "Largo plazo (5+ años)"])
            estrategias = st.multiselect("Estrategias de interés", 
                                       ["Alquiler residencial", "Alquiler comercial", "Rehabilitación y venta", 
                                        "Terrenos", "Remates bancarios", "Rentas vacacionales", "Co-inversiones"])
            
            if st.button("Generar estrategia personalizada"):
                st.session_state['plan_inversion'] = (objetivos, horizonte, ", ".join(estrategias))
                ingresos, gastos, activos, pasivos = st.session_state['datos_financieros']
                analisis_ia = generar_plan_trabajo(ingresos, gastos, activos, pasivos)
                
                st.subheader("🧠 Estrategia Personalizada con IA")
                st.write(analisis_ia)
                st.session_state['reporte_data']['analisis']['analisis_ia'] = analisis_ia
    
    # Paso 4: Plan de retiro con bienes raíces
    if 'usuario_id' in st.session_state and 'datos_financieros' in st.session_state:
        with st.container():
            st.subheader("👴 Plan de Retiro con Bienes Raíces")
            
            col1, col2 = st.columns(2)
            edad_actual = col1.number_input("Tu edad actual", min_value=18, max_value=100, value=30)
            edad_retiro = col2.number_input("Edad de retiro deseada", min_value=edad_actual+1, max_value=100, value=65)
            
            ingresos_retiro = parse_currency(
                st.text_input("Ingresos anuales esperados durante el retiro ($)", value="$40,000")
            )
            gastos_retiro = parse_currency(
                st.text_input("Gastos anuales esperados durante el retiro ($)", value="$30,000")
            )
            ahorros_retiro = parse_currency(
                st.text_input("Ahorros actuales para el retiro ($)", value="$10,000")
            )
            
            if st.button("Calcular proyección de retiro con bienes raíces"):
                ingresos, gastos, activos, pasivos = st.session_state['datos_financieros']
                flujo_caja = ingresos - gastos
                patrimonio_neto = activos - pasivos
                
                analisis = analizar_proyeccion_retiro(edad_actual, edad_retiro, ingresos_retiro, gastos_retiro, ahorros_retiro, patrimonio_neto, flujo_caja)
                st.session_state['reporte_data']['analisis']['proyeccion_retiro'] = analisis
                
                st.subheader("📊 Proyección de Retiro con Bienes Raíces")
                st.write(f"**Años hasta el retiro:** {analisis['años_ahorro']}")
                st.write(f"**Necesidad total estimada:** {format_currency(analisis['necesidad_total'])}")
                st.write(f"**Ahorros actuales:** {format_currency(ahorros_retiro)}")
                st.write(f"**Necesitas ahorrar aproximadamente:** {format_currency(analisis['ahorro_necesario_anual'])} anuales")
                
                st.subheader("🏡 Estrategias con Bienes Raíces para tu Retiro")
                st.write("1. **Propiedades generadoras de ingreso pasivo:** Adquiere propiedades en alquiler que cubran tus gastos de retiro")
                st.write("2. **Apreciación de capital:** Invierte en zonas con potencial de crecimiento para vender con ganancia al retirarte")
                st.write("3. **Fondos inmobiliarios (REITs):** Alternativa más líquida para exposición al mercado inmobiliario")
                
                st.subheader("🎓 Recursos Educativos para Preparar tu Retiro")
                st.markdown("""
                - [Curso: Bienes Raíces para el Retiro](https://investly.com/cursos/retiro)
                - [Seminario: Estrategias de Ingreso Pasivo](https://investly.com/seminarios/ingreso-pasivo)
                - [Guía: Planificación Financiera para el Retiro](https://investly.com/guias/retiro)
                """)
    
    # Botón para descargar PDF
    if 'reporte_data' in st.session_state and st.session_state['reporte_data']['usuario']:
        if st.button("📄 Descargar Reporte Completo en PDF"):
            pdf_bytes = generate_pdf(
                st.session_state['reporte_data']['usuario'],
                st.session_state['reporte_data']['finanzas'],
                st.session_state['reporte_data']['analisis']
            )
            
            st.success("Reporte generado con éxito!")
            
            # Crear enlace de descarga
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="reporte_investly.pdf">Haz clic aquí para descargar tu reporte</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    # Pie de página
    st.markdown("---")
    st.markdown("""
    <div class="calculator-container">
        <h3>📌 Próximos Pasos</h3>
        <ul>
            <li>Revisa nuestros <a href="https://investly.com/cursos" target="_blank">cursos especializados</a> para más estrategias</li>
            <li>Consulta nuestro <a href="https://investly.com/blog" target="_blank">blog educativo</a> para artículos actualizados</li>
            <li>Asiste a nuestros eventos presenciales y online</li>
            <li>Comienza con una propiedad pequeña y escala progresivamente</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    crear_base_datos()
    main()