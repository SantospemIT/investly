import streamlit as st
import sqlite3
import stripe
from datetime import datetime
import supabase
import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Investly - Tu Asesor Financiero",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar variables de sesión
if 'user' not in st.session_state:
    st.session_state.user = None
if 'show_upgrade' not in st.session_state:
    st.session_state.show_upgrade = False
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Configuración desde variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://embmafaufiiuzwfosdfk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVtYm1hZmF1ZmlpdXp3Zm9zZGZrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU3OTI0MTUsImV4cCI6MjA3MTM2ODQxNX0.g4QG3cMsSjs1tvwRTQtSAUTXlio8yRt6FqbO9lXut1o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# Configuración de Stripe
STRIPE_CONFIG = {
    "api_key": os.getenv("STRIPE_API_KEY", "sk_test_..."),
    "price_id": os.getenv("STRIPE_PRICE_ID", "price_..."),
    "success_url": os.getenv("SUCCESS_URL", "http://localhost:8501/success"),
    "cancel_url": os.getenv("CANCEL_URL", "http://localhost:8501/")
}

# Inicializar Supabase
def init_supabase():
    try:
        return supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Error inicializando Supabase: {str(e)}")
        return None

# Funciones de base de datos
def init_db():
    """Inicializar la base de datos SQLite"""
    try:
        conn = sqlite3.connect('investly.db')
        c = conn.cursor()
        
        # Crear tabla de usuarios si no existe
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                subscription_status BOOLEAN DEFAULT FALSE,
                subscription_end DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Crear tabla de evaluaciones si no existe
        c.execute('''
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                evaluation_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users (email)
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error inicializando base de datos: {str(e)}")
        return False

def save_user_data(user_email):
    """Guardar datos del usuario en la base de datos"""
    try:
        conn = sqlite3.connect('investly.db')
        c = conn.cursor()
        
        # Insertar usuario si no existe
        c.execute('''
            INSERT OR IGNORE INTO users (email) VALUES (?)
        ''', (user_email,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error guardando datos de usuario: {str(e)}")
        return False

def get_user_subscription_status(user_email):
    """Obtener estado de suscripción del usuario"""
    try:
        conn = sqlite3.connect('investly.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT subscription_status, subscription_end 
            FROM users 
            WHERE email = ?
        ''', (user_email,))
        
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            # Verificar si la suscripción no ha expirado
            if result[1] and datetime.strptime(result[1], '%Y-%m-%d') > datetime.now():
                return True
        return False
    except:
        return False

# Funciones de autenticación
def authenticate_user():
    """Manejar la autenticación del usuario"""
    # Si ya está autenticado, retornar usuario
    if st.session_state.get('authenticated') and st.session_state.get('user'):
        return st.session_state.user
    
    # Mostrar formulario de autenticación
    st.title("Investly - Inicio de Sesión")
    
    # Formulario de inicio de sesión
    with st.form("login_form"):
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar sesión")
        
        if submitted:
            if email and password:
                # Aquí iría la validación real con Supabase
                # Por ahora usamos una verificación simple para demo
                st.session_state.user = {"email": email}
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Por favor, completa todos los campos")
    
    # Opción de registro
    with st.expander("¿No tienes cuenta? Regístrate aquí"):
        with st.form("register_form"):
            new_email = st.text_input("Correo electrónico (registro)")
            new_password = st.text_input("Contraseña", type="password", key="reg_password")
            confirm_password = st.text_input("Confirmar contraseña", type="password")
            registered = st.form_submit_button("Crear cuenta")
            
            if registered:
                if new_email and new_password and confirm_password:
                    if new_password == confirm_password:
                        st.success("Cuenta creada exitosamente. Ahora puedes iniciar sesión.")
                        # En una implementación real, aquí crearías el usuario en Supabase
                    else:
                        st.error("Las contraseñas no coinciden")
                else:
                    st.error("Por favor, completa todos los campos")
    
    return None

# Funciones de suscripción
def check_subscription_status(user_email):
    """Verificar el estado de suscripción del usuario"""
    return get_user_subscription_status(user_email)

def create_checkout_session(user_email):
    """Crear sesión de checkout de Stripe"""
    try:
        stripe.api_key = STRIPE_CONFIG["api_key"]
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_CONFIG["price_id"],
                'quantity': 1,
            }],
            mode='subscription',
            customer_email=user_email,
            success_url=STRIPE_CONFIG["success_url"] + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=STRIPE_CONFIG["cancel_url"],
            metadata={
                "user_email": user_email
            }
        )
        return session.url
    except Exception as e:
        st.error(f"Error al procesar pago: {str(e)}")
        return None

def show_pro_upgrade_ui():
    """Mostrar interfaz para actualizar a Pro"""
    st.session_state.show_upgrade = True

# Funciones de UI
def show_pro_features_sidebar():
    """Mostrar características Pro en la barra lateral"""
    with st.sidebar.expander("Funcionalidades Pro"):
        st.write("✅ Reportes PDF avanzados")
        st.write("✅ Planes con IA ilimitados")
        st.write("✅ Historial de evaluaciones")
        st.write("✅ Comparación de escenarios")
        st.write("✅ Cursos recomendados")
        st.write("✅ Grupo VIP")
        st.write("✅ Consultoría mensual")

def show_free_dashboard():
    """Mostrar dashboard para usuarios gratuitos"""
    st.title("Investly - Tu Asesor Financiero")
    st.subheader("Plan Gratuito")
    
    st.write("Características disponibles:")
    st.write("✅ Perfil de inversión")
    st.write("✅ Reporte PDF básico")
    st.write("✅ Plan con IA (1 vez)")
    
    # Ejemplo de funcionalidad gratuita
    st.markdown("---")
    st.subheader("Generar Reporte Básico")
    
    with st.form("basic_report_form"):
        investment_amount = st.number_input("Monto a invertir ($)", min_value=100, value=1000, key="free_amount")
        risk_tolerance = st.select_slider("Tolerancia al riesgo", options=["Baja", "Media", "Alta"], key="free_risk")
        
        submitted = st.form_submit_button("Generar Reporte Básico")
        if submitted:
            st.success("Reporte básico generado exitosamente")
    
    # Mostrar opción para mejorar
    st.markdown("---")
    st.info("Desbloquea todas las funciones con Investly Pro")
    if st.button("Mejorar a Pro ahora", key="upgrade_button"):
        show_pro_upgrade_ui()

def show_pro_dashboard():
    """Mostrar dashboard para usuarios Pro"""
    st.title("Investly Pro - Dashboard Premium")
    
    st.write("Características premium:")
    st.write("✅ Reportes PDF avanzados con gráficos")
    st.write("✅ Planes con IA ilimitados")
    st.write("✅ Historial de evaluaciones")
    st.write("✅ Comparación de escenarios")
    st.write("✅ Cursos recomendados exclusivos")
    st.write("✅ Grupo VIP de inversionistas")
    st.write("✅ Consultoría mensual (30 min)")
    
    # Ejemplo de funcionalidad premium
    st.markdown("---")
    st.subheader("Generar Nuevo Reporte Premium")
    
    with st.form("premium_report_form"):
        investment_amount = st.number_input("Monto a invertir ($)", min_value=100, value=1000, key="pro_amount")
        risk_tolerance = st.select_slider("Tolerancia al riesgo", options=["Baja", "Media", "Alta"], key="pro_risk")
        investment_goal = st.selectbox("Objetivo de inversión", 
                                     ["Crecimiento a largo plazo", "Ingreso regular", "Preservación de capital"],
                                     key="pro_goal")
        
        submitted = st.form_submit_button("Generar Reporte Premium")
        if submitted:
            st.success("Reporte premium generado con análisis avanzado y gráficos personalizados")

def show_billing_page():
    """Mostrar página de facturación"""
    st.title("Actualizar a Investly Pro")
    
    user_email = st.session_state.user['email']
    
    st.success("Estás a un paso de desbloquear todas las funciones premium de Investly")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Plan Pro - $19.99/mes")
        st.write("✅ Reportes PDF avanzados con gráficos")
        st.write("✅ Planes con IA ilimitados")
        st.write("✅ Historial de evaluaciones")
        st.write("✅ Comparación de escenarios")
        st.write("✅ Cursos recomendados exclusivos")
        st.write("✅ Grupo VIP de inversionistas")
        st.write("✅ Consultoría mensual (30 min)")
    
    with col2:
        st.subheader("Completa tu suscripción")
        if st.button("Suscribirse ahora con tarjeta", key="stripe_button"):
            checkout_url = create_checkout_session(user_email)
            if checkout_url:
                st.markdown(f"[Ir a pago seguro]({checkout_url})", unsafe_allow_html=True)
    
    st.markdown("---")
    st.info("💳 Tu pago es procesado de forma segura con Stripe. Puedes cancelar tu suscripción en cualquier momento.")
    
    if st.button("Volver al dashboard", key="back_button"):
        st.session_state.show_upgrade = False
        st.rerun()

# Función principal
def main():
    # Inicializar base de datos
    if not init_db():
        st.error("Error inicializando la aplicación. Por favor, intenta nuevamente.")
        return
    
    # Mostrar página de facturación si está solicitada
    if st.session_state.get('show_upgrade'):
        show_billing_page()
        return
    
    # Autenticación
    user = authenticate_user()
    if not user:
        return
    
    # Guardar información del usuario
    user_email = user['email']
    if not save_user_data(user_email):
        st.error("Error guardando información del usuario")
    
    # Verificar estado de suscripción
    is_pro = check_subscription_status(user_email)
    
    # UI principal
    st.sidebar.title(f"Hola, {user_email.split('@')[0]}")
    
    if is_pro:
        st.sidebar.success("✅ Plan Pro Activado")
        show_pro_features_sidebar()
    else:
        st.sidebar.info("🚀 Actualiza a Pro para más funciones")
        if st.sidebar.button("👉 Mejorar a Pro", key="sidebar_upgrade"):
            show_pro_upgrade_ui()
    
    # Cerrar sesión
    if st.sidebar.button("Cerrar sesión", key="logout_button"):
        st.session_state.user = None
        st.session_state.authenticated = False
        st.session_state.show_upgrade = False
        st.rerun()
    
    # Contenido principal según suscripción
    if is_pro:
        show_pro_dashboard()
    else:
        show_free_dashboard()

if __name__ == "__main__":
    main()