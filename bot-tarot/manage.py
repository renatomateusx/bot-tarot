import os
import sys
import requests
from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import HttpResponse, JsonResponse
from django.urls import path
from django.core.wsgi import get_wsgi_application
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client  # Import correto
import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI
import random
import base64
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import json
from PIL import Image


OPENAI_API_KEY = ""
TWILIO_ACCOUNT_SID = "" #""
TWILIO_AUTH_TOKEN =  "" #"
TWILIO_WHATSAPP_FROM = "+19206898558"  # padrão Twilio

openAIClient = OpenAI(api_key=OPENAI_API_KEY)

# --- Django Settings Inline ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

settings.configure(
    DEBUG=True,
    SECRET_KEY='your-secret-key',
    ROOT_URLCONF=__name__,
    ALLOWED_HOSTS=['*'],
    APPEND_SLASH=False,
    MIDDLEWARE=[
        'django.middleware.common.CommonMiddleware',
    ],
)

CARTAS_TAROT = [
    "cartas/00.jpeg", "cartas/01.jpeg", "cartas/02.jpeg", "cartas/03.jpeg",
    "cartas/04.jpeg", "cartas/05.jpeg", "cartas/06.jpeg", "cartas/07.jpeg",
    "cartas/08.jpeg", "cartas/09.jpeg", "cartas/10.jpeg", "cartas/11.jpeg",
    "cartas/12.jpeg", "cartas/13.jpeg", "cartas/14.jpeg", "cartas/15.jpeg",
    "cartas/16.jpeg", "cartas/17.jpeg", "cartas/18.jpeg", "cartas/19.jpeg",
    "cartas/20.jpeg", "cartas/21.jpeg"
]

account_sid = TWILIO_ACCOUNT_SID
auth_token = TWILIO_AUTH_TOKEN
twilio_number = TWILIO_WHATSAPP_FROM

client = Client(account_sid, auth_token)

# --- Firebase Init ---
cred_path = os.path.join(BASE_DIR, 'bot-tarot-f6b40-firebase-adminsdk-fbsvc-25b1790aa1.json')
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print("⚠️ firebase-key.json not found.")
    db = None

# ------- User Manipulation -------

def is_active_user(phone):
    doc = db.collection('users').document(phone).get()
    return doc.exists and doc.to_dict().get('active', False)

def mark_user_active(phone):
    db.collection('users').document(phone).set({
        'active': True,
        'next_question': (datetime.utcnow() + timedelta(days=30)).isoformat()
    }, merge=True)

def update_next_question_date(phone):
    db.collection('users').document(phone).update({
        'next_question': (datetime.utcnow() + timedelta(days=30)).isoformat()
    })

def can_ask_question(phone):
    user_doc = db.collection('users').document(phone).get()

    if not user_doc.exists:
        return False  # Usuário não encontrado, não pode perguntar.

    user_data = user_doc.to_dict()
    next_question_str = user_data.get('next_question')

    if not next_question_str:
        # Se não tiver next_question, libera a pergunta (primeira vez).
        return True

    next_question = datetime.fromisoformat(next_question_str)

    return datetime.utcnow() >= next_question

def get_all_active_users():
    docs = db.collection("users").where("active", "==", True).stream()
    return [doc.id for doc in docs]

# -- Sort Cards ----
def sort_cards(qtd=3):
    return random.sample(CARTAS_TAROT, qtd)

# --- Generate message based on cards ---
def gerar_mensagem_cartas(image_paths, pergunta=None):

    image_contents = []
    for path in image_paths:
        with open(path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}"
                }
            })

    # Prompt fixo
    prompt_inicial = (
        "Você é uma taróloga experiente. "
        "Analise as cartas de tarot enviadas e faça uma leitura de amor, profissão e relacionamento "
        "Responda de forma intuitiva, acolhedora e mística. e acolhedora."
        "Use uma linguagem mística, profunda e reconfortante."
    )

    # Parte variável: pergunta ou previsão geral
    prompt_variavel = (
        f" Responda de forma intuitiva e acolhedora à seguinte pergunta do consulente: '{pergunta}'." 
        if pergunta else 
        " Como não há pergunta específica, gere uma previsão geral para a semana com base nas cartas."
    )

    limit = (
        "Sua resposta deve obedecer às seguintes regras: "
        "- No máximo 1024 caracteres (contando espaços). "
        "- No máximo 2 quebras de linha (no máximo 2 '\n\n'). "
        "- Sem emojis. "
        "- Separe a análise de cada carta com o marcador [[CARD]]. Exem O LOUCO ...texto... [[CARD]]. A Justiça ...texto... [[CARD]]"
        "- Cada bloco entre [[CARD]] deve ter no máximo 300 caracteres. "
        "- Finalize o texto naturalmente sem extrapolar esses limites e sem cortar a mensagem."
    )

    prompt = prompt_inicial + prompt_variavel + limit
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                *image_contents
            ]
        }
    ]

    response = openAIClient.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        max_tokens=375,
    )
    return response.choices[0].message.content

def generate_tarot_reading(pergunta=None, cartas=sort_cards()):
    return gerar_mensagem_cartas(cartas, pergunta)

def process_paypal_payment(payload):
    # Você pode validar assinatura do PayPal aqui se quiser
    payer_info = payload.get("resource", {}).get("payer", {}).get("payer_info", {})
    phone = payer_info.get("phone", {}).get("national_number") or payer_info.get("email")
    return phone

def createImage(fileName, cardsPath, pasta_saida="combined_images"):

    # Garante que a pasta de saída existe
    os.makedirs(pasta_saida, exist_ok=True)

    # Abre todas as imagens
    cartas = [Image.open(img_path) for img_path in cardsPath]

    # Assume que todas as imagens têm a mesma altura
    largura_total = sum(carta.width for carta in cartas)
    altura_maxima = max(carta.height for carta in cartas)

    # Cria imagem em branco (fundo branco)
    imagem_final = Image.new('RGB', (largura_total, altura_maxima), color=(255, 255, 255))

    # Cola as cartas uma do lado da outra
    x_offset = 0
    for carta in cartas:
        imagem_final.paste(carta, (x_offset, 0))
        x_offset += carta.width

    # Nome do arquivo: ex. whatsapp_5511999999999.jpg
    nome_arquivo = f"{fileName.replace('+', '')}.jpg"
    caminho_arquivo = os.path.join(pasta_saida, nome_arquivo)

    # Salva a imagem final
    imagem_final.save(caminho_arquivo)

    print(f"Imaged saved in: {caminho_arquivo}")
    return nome_arquivo

# ------- WhatsApp Message --------
def send_whatsapp_message(to, body, media_name=None):

    if media_name:

        media_sent = client.messages.create(
            from_=f"whatsapp:{twilio_number}",
            to=f"whatsapp:+{to}",
            content_sid="HXb9f767ca60775d53aa407cbd64bbc6c9",
            media_url=f"https://rmms.tech/tarot/combined_images/{media_name}",
        )
        parts = body.split('[[CARD]]')
        
        for part in parts:
            if part.strip():
                client.messages.create(
                    from_=f"whatsapp:{twilio_number}",
                    to=f"whatsapp:+{to}",
                    content_sid="HXf9e8b8bc9780e6c29e83f181d1756af4",
                    content_variables=json.dumps({ "body": part })
                )
    else:
        
        return client.messages.create(
            from_=f"whatsapp:{twilio_number}",
            to=f"whatsapp:+{to}",
            content_sid="HXb7864ae943ca4345070ee322283747db",
            content_variables=json.dumps({ "url_assinatura": body })
        )

# --- Weekly method routine ----
def send_all_tarot():
    # users = get_all_active_users()
    users = [user.strip() for user in get_all_active_users()]
    
    cartas = sort_cards()
    mensagem = generate_tarot_reading(cartas=cartas)
    
    for user in users:
        media_url = createImage(user,cardsPath=cartas)
    
        send_whatsapp_message(user, f"{mensagem}", media_url)

# --- Main scheduler method ----
def schedule_tasks():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_all_tarot, 'cron', day_of_week='sun', hour=8)
    scheduler.start()

# --- View: Webhook ---

@csrf_exempt
def twilio_webhook(request):
    
    if request.method == 'POST':
        from_number = request.POST.get('From', '').replace('whatsapp:', '')
        body = request.POST.get('Body', '').strip().lower()

        if not is_active_user(from_number):
            url = "https://rmms.tech"
            send_whatsapp_message(from_number, url)
            return JsonResponse({"message": "Usuário não ativo"}, status=200)

        if body == 'cancelar':
            # Atualizar no Firebase como inativo
            return JsonResponse({"message": "Assinatura cancelada"}, status=200)

        if body.startswith('pergunta'):
            if not can_ask_question(from_number):
                return JsonResponse({"message": "Pergunta não permitida no momento"}, status=200)
            
            cartas = sort_cards()
            texto = request.POST.get('Body')[8:].strip()
            media_url = createImage(from_number, cardsPath=cartas)
            resposta = generate_tarot_reading(texto, cartas)
    
            send_whatsapp_message(from_number, resposta, media_url)
            update_next_question_date(from_number)
            return JsonResponse({"message": "Pergunta respondida"}, status=200)

        return JsonResponse({"message": "Comando não reconhecido"}, status=200)
    if request.method == 'GET':
        return JsonResponse({"message": "Comando não reconhecido"}, status=200)

@csrf_exempt
def paypal_webhook(request):
    if request.method == 'POST':
        payload = json.loads(request.body)
        user_phone = process_paypal_payment(payload)
        mark_user_active(user_phone)
        send_whatsapp_message(user_phone, "Bem-vindo! Você pode enviar uma pergunta com o comando 'Pergunta: ...'")
        return JsonResponse({"status": "ok"})

    return JsonResponse({"error": "Método não permitido"}, status=405)

# ----- Web API -------
@csrf_exempt
def send_weekly_tarot(request):
    if request.method == 'POST':
        send_all_tarot()
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Método não permitido"}, status=405)

# --- URLConf ---
urlpatterns = [
    path('webhook/', twilio_webhook, name='twilio_webhook'),
    path('paypal_webhook/', paypal_webhook, name='paypal_webhook'),
    path('send_weekly_tarot/', send_weekly_tarot, name='send_weekly_tarot'),
]

# --- Entry Point ---
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '__main__')
    application = get_wsgi_application()
    schedule_tasks()
    execute_from_command_line(sys.argv)
