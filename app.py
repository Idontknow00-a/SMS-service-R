from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
import time
from threading import Timer
import logging
import os
import re
import imaplib
import email as email_lib
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ================= CONFIGURAÇÃO =================
API_KEY = os.environ.get('API_KEY_SMS', '')
SERVICE = 'ot'             # Any Other
TIMEOUT_DURATION = 120     # segundos
OPERATORS = []             # Lista vazia = TODAS as operadoras

# 🔄 ROTAÇÃO DE PAÍSES (alterna a cada requisição)
COUNTRIES_ROTATION = [151, 73]   # 151 = Chile | 73 = Brasil
# Exemplos:
# COUNTRIES_ROTATION = [151, 73]           # Alterna Chile ↔ Brasil
# COUNTRIES_ROTATION = [151, 73, 33]       # Alterna Chile → Brasil → Colômbia
# COUNTRIES_ROTATION = [151]               # Só Chile (sem rotação)
# COUNTRIES_ROTATION = [73]                # Só Brasil (sem rotação)

# Controle do índice da rotação
current_country_index = 0

# Mapeamento: código do HeroSMS -> DDI (código de discagem internacional)
COUNTRY_DIAL_CODES = {
    151: '56',   # Chile
    33: '57',    # Colômbia
    73: '55',    # Brasil
    54: '52',    # México
    39: '54',    # Argentina
    152: '56',   # Chile (alternativo)
    36: '1',     # Canadá
    16: '44',    # Reino Unido
    12: '1',     # USA (virtual)
    0: '1',      # USA (padrão)
}

# Nomes dos países (para logs)
COUNTRY_NAMES = {
    151: 'Chile',
    33: 'Colômbia',
    73: 'Brasil',
    54: 'México',
    39: 'Argentina',
    152: 'Chile',
    36: 'Canadá',
    16: 'Reino Unido',
    12: 'USA',
}

# Configuração do código via email (IMAP) - NÃO USADO, mas mantido
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', '')
EMAIL_APP_PASSWORD = os.environ.get('EMAIL_APP_PASSWORD', '')
EMAIL_SENDER_FILTRO = 'no-reply@crmbonus.com'
ultimo_codigo_email = None

# Controle de bloqueio
failed_attempts = {}
MAX_FAILURES_BEFORE_COOLDOWN = 3
COOLDOWN_MINUTES = 30

# Armazenamento em memória
number_timeouts = {}
active_numbers = {}
successful_numbers = set()
operator_info = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

BASE_URL = "https://hero-sms.com/stubs/handler_api.php"


# ================= ROTAÇÃO DE PAÍSES =================
def get_next_country():
    """Retorna o próximo país da rotação e incrementa o índice"""
    global current_country_index
    
    if not COUNTRIES_ROTATION:
        return 151  # fallback
    
    country = COUNTRIES_ROTATION[current_country_index % len(COUNTRIES_ROTATION)]
    current_country_index += 1
    
    logger.info(f"🔄 Rotação: usando país {country} ({COUNTRY_NAMES.get(country, '?')}) - índice {current_country_index}")
    return country


# ================= EXTRAÇÃO DE CÓDIGO =================
def extrair_codigo(texto):
    """Extrai apenas o código numérico da mensagem SMS"""
    if not texto:
        return texto
    
    if texto.isdigit():
        return texto
    
    match = re.search(r'(?:code|c[oó]digo|is)\s*[:=]?\s*(\d{4,8})', texto, re.IGNORECASE)
    if match:
        return match.group(1)
    
    match = re.search(r'[:=]\s*(\d{4,8})', texto)
    if match:
        return match.group(1)
    
    match = re.search(r'\b(\d{4,8})\b', texto)
    if match:
        return match.group(1)
    
    return texto


# ================= LIMPEZA DE NÚMERO =================
def limpar_numero(raw_number, country_code):
    """Remove formatação e DDI do número, retornando só os dígitos locais"""
    if not raw_number:
        return raw_number
    
    clean = re.sub(r'\D', '', raw_number)
    
    dial_code = COUNTRY_DIAL_CODES.get(country_code)
    if dial_code and clean.startswith(dial_code):
        clean = clean[len(dial_code):]
    
    return clean


# ================= FUNÇÕES AUXILIARES =================
def check_failure_rate():
    now = datetime.now()
    recent_failures = sum(1 for t in failed_attempts.values()
                          if (now - t).seconds < COOLDOWN_MINUTES * 60)
    if recent_failures >= MAX_FAILURES_BEFORE_COOLDOWN:
        logger.warning(f"⚠️ Muitas falhas recentes ({recent_failures}). Aguarde...")
        return True
    return False


def get_available_operators(country_code):
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getOperators&country={country_code}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country_operators = data.get('countryOperators', {})
                operators = country_operators.get(str(country_code), [])
                logger.info(f"Operadoras disponíveis no país {country_code}: {operators}")
                return operators
        return []
    except Exception as e:
        logger.error(f"Erro ao obter operadoras: {e}")
        return []


def get_service_price(country_code):
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getPrices&service={SERVICE}&country={country_code}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and str(country_code) in data:
                country_data = data[str(country_code)]
                if isinstance(country_data, dict) and SERVICE in country_data:
                    service_info = country_data[SERVICE]
                    if isinstance(service_info, dict) and 'cost' in service_info:
                        price = float(service_info['cost'])
                        return f"${price:.4f}"
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and SERVICE in item:
                        service_info = item[SERVICE]
                        if isinstance(service_info, dict) and 'cost' in service_info:
                            price = float(service_info['cost'])
                            return f"${price:.4f}"
    except Exception as e:
        logger.error(f"Erro ao obter preço: {e}")
    return "$0.00"


def get_number_from_country(country_code):
    """Tenta obter um número de um país específico"""
    try:
        price = get_service_price(country_code)

        if not OPERATORS:
            url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={SERVICE}&country={country_code}"
            logger.info(f"📞 Buscando número do país {country_code} ({COUNTRY_NAMES.get(country_code, '?')}) SEM filtro")
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.text.strip()
                logger.info(f"📥 Resposta: {data}")

                if data.startswith('ACCESS_NUMBER'):
                    parts = data.split(':')
                    number_id = parts[1].strip() if len(parts) > 1 else ''
                    operator_info[number_id] = 'AUTO'
                    return data, price, country_code
                else:
                    return data, price, country_code

            return 'NO_NUMBERS', price, country_code

        available_operators = get_available_operators(country_code)
        if not available_operators:
            return 'NO_NUMBERS', price, country_code

        filtered = [op for op in available_operators if op.lower() in [o.lower() for o in OPERATORS]]
        if not filtered:
            return 'NO_NUMBERS', price, country_code

        for operator in filtered:
            url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={SERVICE}&country={country_code}&operator={operator}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.text.strip()
                if data.startswith('ACCESS_NUMBER'):
                    parts = data.split(':')
                    number_id = parts[1].strip() if len(parts) > 1 else ''
                    operator_info[number_id] = operator.upper()
                    return data, price, country_code
                elif 'NO_NUMBERS' in data:
                    continue
                elif 'NO_BALANCE' in data:
                    return 'NO_BALANCE', price, country_code
                elif 'BAD_KEY' in data:
                    return 'BAD_KEY', price, country_code

        return 'NO_NUMBERS', price, country_code

    except Exception as e:
        logger.error(f"Erro ao obter número: {e}")
        return 'NO_NUMBER', "$0.00", country_code


def get_number():
    """Obtém um número rotacionando entre países"""
    if check_failure_rate():
        logger.warning("⚠️ Período de espera para evitar bloqueio")
        return 'RATE_LIMIT', "$0.00", None

    # Pega o próximo país da rotação
    primary_country = get_next_country()

    # Tenta o país principal
    data, price, country = get_number_from_country(primary_country)

    # Se falhou e há outros países na rotação, tenta os próximos
    if not data.startswith('ACCESS_NUMBER'):
        logger.warning(f"⚠️ Falha no país {primary_country} ({data}). Tentando outros...")
        for _ in range(len(COUNTRIES_ROTATION) - 1):
            next_country = get_next_country()
            data, price, country = get_number_from_country(next_country)
            if data.startswith('ACCESS_NUMBER'):
                break

    return data, price, country


def setup_timeout(number_id):
    def cleanup_memory():
        try:
            number_timeouts.pop(number_id, None)
            active_numbers.pop(number_id, None)
            operator_info.pop(number_id, None)
            logger.info(f"⏰ Limpeza de memória para {number_id}")
        except Exception as e:
            logger.error(f"Erro na limpeza: {e}")

    timer = Timer(TIMEOUT_DURATION, cleanup_memory)
    timer.start()
    number_timeouts[number_id] = timer
    return timer


def request_sms_resend(number_id):
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&id={number_id}&status=3"
        response = requests.get(url, timeout=10)
        data = response.text.strip()
        logger.info(f"📤 Solicitando reenvio SMS para {number_id}: {data}")

        if data == 'ACCESS_RETRY_GET':
            return True, "SMS solicitado com sucesso"
        elif data == 'ACCESS_ACTIVATION':
            return True, "Ativação ainda ativa, aguardando SMS"
        else:
            return False, f"Erro ao solicitar SMS: {data}"
    except Exception as e:
        logger.error(f"Erro ao solicitar reenvio: {e}")
        return False, str(e)


# ================= FUNÇÕES DE EMAIL (mantidas) =================
def _extrair_texto_email(msg):
    corpo_plain, corpo_html = None, None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    if content_type == 'text/plain' and corpo_plain is None:
                        corpo_plain = payload.decode('utf-8', errors='ignore')
                    elif content_type == 'text/html' and corpo_html is None:
                        corpo_html = payload.decode('utf-8', errors='ignore')
            except:
                continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                texto = payload.decode('utf-8', errors='ignore')
                if msg.get_content_type() == 'text/html':
                    corpo_html = texto
                else:
                    corpo_plain = texto
        except:
            pass

    bruto = corpo_plain or corpo_html or ''
    
    if corpo_html and not corpo_plain:
        bruto = re.sub(r'<style[\s\S]*?</style>', ' ', bruto, flags=re.IGNORECASE)
        bruto = re.sub(r'<script[\s\S]*?</script>', ' ', bruto, flags=re.IGNORECASE)
        bruto = re.sub(r'<[^>]+>', ' ', bruto)
        bruto = bruto.replace('&nbsp;', ' ').replace('&amp;', '&')
        bruto = re.sub(r'\s+', ' ', bruto).strip()
    
    return bruto


def buscar_codigo_email():
    global ultimo_codigo_email

    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        return {'success': False, 'message': 'EMAIL não configurado.'}

    try:
        imap = imaplib.IMAP4_SSL('imap.gmail.com')
        imap.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        imap.select('INBOX')

        status, dados = imap.search(None, f'(FROM "{EMAIL_SENDER_FILTRO}")')
        if status != 'OK' or not dados[0]:
            imap.logout()
            return {'success': False, 'message': 'Nenhum email encontrado.'}

        ids = dados[0].split()
        ultimo_id = ids[-1]
        
        status, msg_dados = imap.fetch(ultimo_id, '(RFC822)')
        imap.logout()
        
        if status != 'OK':
            return {'success': False, 'message': 'Erro ao ler email.'}

        msg = email_lib.message_from_bytes(msg_dados[0][1])
        texto = _extrair_texto_email(msg)
        
        match = re.search(r'\b(\d{4,8})\b', texto)
        if not match:
            return {'success': False, 'message': 'Nenhum código encontrado.'}
        
        novo_codigo = match.group(1)
        
        if ultimo_codigo_email is not None and novo_codigo == ultimo_codigo_email:
            return {'success': False, 'message': 'Código repetido', 'code': novo_codigo}
        
        ultimo_codigo_email = novo_codigo
        return {'success': True, 'code': novo_codigo}

    except Exception as e:
        logger.error(f'Erro ao buscar código: {e}')
        return {'success': False, 'message': f'Erro: {str(e)}'}


# ================= ROTAS =================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_number', methods=['GET'])
def get_number_route():
    try:
        data, price, country_used = get_number()

        if data.startswith('ACCESS_NUMBER'):
            parts = data.split(':', 2)
            number_id = parts[1].strip()
            raw_number = parts[2].strip()

            # Limpa o número usando o DDI do país correto
            phone_number = limpar_numero(raw_number, country_used)
            logger.info(f"📱 [{COUNTRY_NAMES.get(country_used, '?')}] Número bruto: {raw_number} → Limpo: {phone_number}")

            op = operator_info.get(number_id, 'AUTO')

            setup_timeout(number_id)
            active_numbers[number_id] = {
                'phone_number': phone_number,
                'raw_number': raw_number,
                'operator': op,
                'price': price,
                'country': country_used,
                'country_name': COUNTRY_NAMES.get(country_used, '?'),
                'status': 'waiting',
                'created_at': time.time(),
                'received_codes': []
            }

            return jsonify({
                'success': True,
                'number_id': number_id,
                'phone_number': phone_number,
                'operator': op,
                'price': price,
                'country': country_used,
                'country_name': COUNTRY_NAMES.get(country_used, '?'),
                'message': f'Número obtido com sucesso'
            })
        else:
            failed_attempts[time.time()] = datetime.now()

            msg_map = {
                'NO_BALANCE': 'Saldo insuficiente!',
                'NO_NUMBERS': 'Sem números disponíveis em nenhum país',
                'BAD_KEY': 'API Key inválida',
                'RATE_LIMIT': 'Aguarde - Muitas tentativas'
            }
            return jsonify({
                'success': False,
                'message': msg_map.get(data, f'Erro: {data}')
            })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500


@app.route('/request_new_sms/<number_id>', methods=['GET'])
def request_new_sms_route(number_id):
    try:
        success, message = request_sms_resend(number_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@app.route('/get_status/<number_id>', methods=['GET'])
def get_status(number_id):
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getStatus&id={number_id}"
        response = requests.get(url, timeout=10)
        data = response.text.strip()

        result = {'success': True, 'has_code': False, 'code': None, 'status': 'waiting'}

        if data.startswith('STATUS_OK:'):
            code_raw = data.split(':', 1)[1].strip()
            logger.info(f"📩 Mensagem bruta: {code_raw}")
            
            code = extrair_codigo(code_raw)
            logger.info(f"✅ Código extraído: {code}")

            if number_id in active_numbers:
                received_codes = active_numbers[number_id].get('received_codes', [])
                if code in received_codes:
                    result.update({
                        'has_code': False, 'code': None,
                        'status': 'waiting_new_code',
                        'message': 'Aguardando novo código...'
                    })
                    return jsonify(result)

            if number_id in number_timeouts:
                number_timeouts[number_id].cancel()
                del number_timeouts[number_id]

            if number_id not in successful_numbers:
                successful_numbers.add(number_id)

            if number_id in active_numbers:
                active_numbers[number_id]['received_codes'].append(code)
                active_numbers[number_id]['last_code'] = code
                active_numbers[number_id]['status'] = 'code_received'

            result.update({'has_code': True, 'code': code, 'status': 'received'})

        elif data == 'STATUS_WAIT_CODE':
            result.update({'message': 'Aguardando código...', 'status': 'waiting_code'})

        elif data in ('STATUS_CANCEL', 'STATUS_WAIT_RETRY'):
            result.update({'message': 'Número expirado', 'status': 'cancelled'})
            active_numbers.pop(number_id, None)
            operator_info.pop(number_id, None)

        else:
            result.update({'message': data, 'status': 'unknown'})

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@app.route('/get_email_code', methods=['GET'])
def get_email_code_route():
    try:
        resultado = buscar_codigo_email()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'success': True,
        'countries_rotation': COUNTRIES_ROTATION,
        'countries_rotation_names': [COUNTRY_NAMES.get(c, str(c)) for c in COUNTRIES_ROTATION],
        'current_index': current_country_index,
        'next_country': COUNTRIES_ROTATION[current_country_index % len(COUNTRIES_ROTATION)] if COUNTRIES_ROTATION else None,
        'service': SERVICE,
        'operators_filter': OPERATORS,
        'successful_numbers': len(successful_numbers),
        'active_numbers': len(active_numbers),
        'total_codes': sum(len(num.get('received_codes', [])) for num in active_numbers.values()),
    })


if __name__ == '__main__':
    logger.info("🚀 Servidor SMS iniciado (HeroSMS)")
    logger.info(f"🔄 Rotação de países: {' → '.join([COUNTRY_NAMES.get(c, str(c)) for c in COUNTRIES_ROTATION])}")
    logger.info(f"📦 Serviço: {SERVICE} (Any Other)")
    logger.info(f"📱 Operadoras: TODAS (filtro desativado)")
    logger.info("⏰ Timeout: 120s")
    logger.info("✂️  Extração automática de código ativada")
    logger.info("🧹 Remoção automática de DDI ativada")
    app.run(debug=True, port=3000, host='0.0.0.0')
