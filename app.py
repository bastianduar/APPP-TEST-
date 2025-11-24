import streamlit as st
import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
from typing import List

# --- Pydantic Schema for Data Validation ---
class SalesAngle(BaseModel):
    """A single sales angle (avatar) with a persuasive paragraph."""
    avatar_name: str = Field(..., description="A creative name for the customer avatar, e.g., 'El Escéptico', 'El Usuario Intensivo'.")
    pain_point_addressed: str = Field(..., description="The main customer pain point this angle addresses, detected from the reviews.")
    persuasive_copy: str = Field(..., description="A short, persuasive sales paragraph (3-5 sentences) tailored to this avatar, written by a Direct Response Marketing expert.")

class StrategyOutput(BaseModel):
    """The complete marketing strategy output."""
    main_pain_points: List[str] = Field(..., description="A list of the 3 main customer pain points detected from the reviews.")
    sales_angles: List[SalesAngle] = Field(..., description="A list of 3 distinct sales angles (avatars) with tailored persuasive copy.")

# --- Streamlit UI Configuration and Styling ---
st.set_page_config(layout="centered", page_title="Dropshipping Strategy Generator")

# Minimalist Styling (The Black Sheep style)
st.markdown("""
    <style>
    .stApp {
        background-color: white;
        color: black;
    }
    .stButton>button {
        background-color: black;
        color: white;
        border: 1px solid black;
        border-radius: 5px;
        padding: 10px 24px;
        font-size: 16px;
        font-weight: bold;
        transition: background-color 0.3s, color 0.3s;
    }
    .stButton>button:hover {
        background-color: #333333;
        color: white;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border: 1px solid black;
        color: black;
    }
    .stRadio div {
        color: black;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Dropshipping Strategy Generator")

# --- Sidebar for API Key Input ---
with st.sidebar:
    st.header("Configuración")
    openai_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="Ingresa tu clave de API de OpenAI. La aplicación no funcionará sin ella."
    )
    st.markdown("---")
    st.info("Estilo: Minimalista 'The Black Sheep' (Fondo blanco, texto negro).")

# --- Main Application Logic ---

# Check for API Key
if not openai_api_key:
    st.warning("🚨 Por favor, ingresa tu OpenAI API Key en la barra lateral para comenzar.")
    st.stop()

# Initialize OpenAI Client
try:
    client = OpenAI(api_key=openai_api_key)
except Exception as e:
    st.error(f"Error al inicializar el cliente de OpenAI: {e}")
    st.stop()

# Input Fields
product_name = st.text_input(
    "Nombre del Producto",
    placeholder="Ej: 'Cepillo de dientes sónico ultra-silencioso'",
    key="product_name_input"
)

competitor_reviews = st.text_area(
    "Reseñas de la Competencia (Pega textos largos aquí)",
    height=300,
    placeholder="Pega aquí las reseñas de 5 a 10 clientes de tu competencia. La IA las analizará para encontrar los 'dolores' principales.",
    key="reviews_input"
)

# Action Button
if st.button("GENERAR ESTRATEGIA"):
    if not product_name or not competitor_reviews:
        st.error("Por favor, completa el 'Nombre del Producto' y pega las 'Reseñas de la Competencia'.")
    else:
        with st.spinner("Analizando reseñas y generando ángulos de venta con GPT-4o..."):
            try:
                # --- OpenAI API Call (Using JSON Mode) ---
                
                # 1. Define the JSON schema for the model to follow
                json_schema = StrategyOutput.model_json_schema()

                # 2. Construct the prompt
                prompt = f"""
                Actúa como un experto en Direct Response Marketing (DRM) con 10 años de experiencia.
                Tu tarea es analizar las reseñas de la competencia para un producto similar al: "{product_name}".

                RESEÑAS A ANALIZAR:
                ---
                {competitor_reviews}
                ---

                Instrucciones:
                1. **Detecta los dolores principales del cliente** (al menos 3) que se mencionan o se infieren de las reseñas.
                2. **Crea 3 'Ángulos de Venta' (Avatares) distintos** basados en estos dolores. Cada ángulo debe representar un tipo de cliente con una objeción o necesidad específica (ej: 'El Escéptico', 'El Usuario Intensivo', 'El Buscador de Valor').
                3. Para cada ángulo, escribe un **párrafo persuasivo de venta** (3-5 frases) que hable directamente al dolor de ese avatar y posicione el producto "{product_name}" como la solución definitiva. El tono debe ser de venta directa y convincente.
                4. Tu respuesta DEBE ser un objeto JSON que se ajuste estrictamente al siguiente esquema: {json.dumps(json_schema, indent=2)}
                """
                
                # 3. Call the API with JSON Mode enabled
                response = client.chat.completions.create(
                    model="gpt-4o",
                    response_format={ "type": "json_object" },
                    messages=[
                        {"role": "system", "content": "You are an expert Direct Response Marketing strategist. You must output a valid JSON object that strictly adheres to the user-provided schema."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8
                )
                
                # 4. Parse and validate the JSON response
                response_json = json.loads(response.choices[0].message.content)
                strategy_output = StrategyOutput.model_validate(response_json)

                st.session_state['strategy'] = strategy_output
                st.session_state['angles'] = {
                    angle.avatar_name: angle for angle in strategy_output.sales_angles
                }
                
                st.success("✅ Estrategia generada con éxito. ¡Elige tu ángulo de venta!")

            except ValidationError as e:
                st.error(f"❌ Error de validación de datos de la API de OpenAI. La respuesta no sigue el formato esperado.\nDetalles: {e}")
                st.stop()
            except json.JSONDecodeError:
                st.error("❌ Error al decodificar la respuesta JSON de la API de OpenAI. La respuesta no es un JSON válido.")
                st.stop()
            except Exception as e:
                st.error(f"❌ Error al comunicarse con la API de OpenAI: {e}")
                st.stop()

# --- Output Section ---
if 'strategy' in st.session_state:
    st.header("Resultados del Análisis")
    
    # Display Pain Points
    st.subheader("Dolores Principales Detectados")
    pain_points_markdown = "\n".join([f"- {pp}" for pp in st.session_state['strategy'].main_pain_points])
    st.markdown(pain_points_markdown)
    
    st.markdown("---")
    
    # Display Angles for Selection
    st.subheader("Ángulos de Venta (Avatares)")
    
    angle_options = list(st.session_state['angles'].keys())
    
    selected_angle_name = st.radio(
        "Selecciona el ángulo que deseas usar para generar el código de Shopify:",
        angle_options,
        key="angle_selector"
    )
    
    if selected_angle_name:
        selected_angle: SalesAngle = st.session_state['angles'][selected_angle_name]
        
        st.markdown("### Párrafo Persuasivo Seleccionado")
        st.markdown(f"**Ángulo:** {selected_angle.avatar_name}")
        st.markdown(f"**Dolor Abordado:** {selected_angle.pain_point_addressed}")
        st.markdown(f"**Copy:** *{selected_angle.persuasive_copy}*")
        
        st.markdown("---")
        
        # --- Shopify JSON Code Generation ---
        st.header("Código Shopify (Sección Hero)")
        
        # Create a simple title based on the product name and angle
        shopify_title = f"¡{selected_angle.avatar_name} Resuelto! El {product_name}"
        
        # Shopify JSON Structure
        shopify_json_data = {
            "type": "hero_section",
            "name": "Hero Section - Generated by AI",
            "settings": [
                {
                    "type": "text",
                    "id": "heading",
                    "label": "Heading",
                    "default": shopify_title
                },
                {
                    "type": "textarea",
                    "id": "text",
                    "label": "Text",
                    "default": selected_angle.persuasive_copy
                },
                # Add other typical hero section settings (e.g., button, image) for completeness
                {
                    "type": "url",
                    "id": "button_link",
                    "label": "Button link"
                },
                {
                    "type": "text",
                    "id": "button_label",
                    "label": "Button label",
                    "default": "Comprar Ahora"
                }
            ]
        }
        
        # Display JSON in a code block
        json_output = json.dumps(shopify_json_data, indent=4, ensure_ascii=False)
        
        st.code(json_output, language="json")
        st.info("👆 Copia este código JSON y pégalo en tu tema de Shopify para crear una sección 'Hero' optimizada para la conversión.")

# --- End of App ---
