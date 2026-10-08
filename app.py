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
COUNTRY_CODE = 73          # 33 = Colômbia (73 = Brasil)
SERVICE = 'ot'             # Any Other
TIMEOUT_DURATION = 120     # segundos
OPERATORS = []             # Lista vazia = TODAS as operadoras

# Configuração do código via email (IMAP) - NÃO USADO AGORA, mas mantido
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


# ================= EXTRAÇÃO DE CÓDIGO =================
def extrair_codigo(texto):
    """Extrai apenas o código numérico da mensagem SMS"""
    if not texto:
        return texto
    
    # Se já é só número, retorna direto
    if texto.isdigit():
        return texto
    
    # Padrão 1: "code is: 123456" ou "código: 123456" ou "code: 123456"
    match = re.search(r'(?:code|c[oó]digo|is)\s*[:=]?\s*(\d{4,8})', texto, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Padrão 2: Número após ":" ou "="
    match = re.search(r'[:=]\s*(\d{4,8})', texto)
    if match:
        return match.group(1)
    
    # Padrão 3: Primeiro número de 4-8 dígitos encontrado
    match = re.search(r'\b(\d{4,8})\b', texto)
    if match:
        return match.group(1)
    
    # Se não achou nada, retorna o texto original
    return texto


# ================= FUNÇÕES AUXILIARES =================
def check_failure_rate():
    now = datetime.now()
    recent_failures = sum(1 for t in failed_attempts.values()
                          if (now - t).seconds < COOLDOWN_MINUTES * 60)
    if recent_failures >= MAX_FAILURES_BEFORE_COOLDOWN:
        logger.warning(f"⚠️ Muitas falhas recentes ({recent_failures}). Aguarde...")
        return True
    return False


def get_available_operators():
    """Obtém a lista de operadoras disponíveis para o país configurado"""
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getOperators&country={COUNTRY_CODE}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country_operators = data.get('countryOperators', {})
                operators = country_operators.get(str(COUNTRY_CODE), [])
                logger.info(f"Operadoras disponíveis no país {COUNTRY_CODE}: {operators}")
                return operators
        return []
    except Exception as e:
        logger.error(f"Erro ao obter operadoras: {e}")
        return []


def get_service_price():
    """Obtém o preço do serviço"""
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getPrices&service={SERVICE}&country={COUNTRY_CODE}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and str(COUNTRY_CODE) in data:
                country_data = data[str(COUNTRY_CODE)]
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


def get_number():
    """Obtém um número. Se OPERATORS estiver vazio, usa TODAS as operadoras."""
    try:
        if check_failure_rate():
            logger.warning("⚠️ Período de espera para evitar bloqueio")
            return 'RATE_LIMIT', "$0.00"

        price = get_service_price()

        # Se OPERATORS está vazio → pede SEM filtro de operadora (API escolhe)
        if not OPERATORS:
            url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={SERVICE}&country={COUNTRY_CODE}"
            logger.info(f"📞 Buscando número SEM filtro de operadora")
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.text.strip()
                logger.info(f"📥 Resposta da API: {data}")

                if data.startswith('ACCESS_NUMBER'):
                    parts = data.split(':')
                    number_id = parts[1].strip() if len(parts) > 1 else ''
                    operator_info[number_id] = 'AUTO'
                    logger.info(f"✓ Número obtido (operadora automática)")
                    return data, price
                elif 'NO_BALANCE' in data:
                    return 'NO_BALANCE', price
                elif 'BAD_KEY' in data:
                    return 'BAD_KEY', price
                elif 'NO_NUMBERS' in data:
                    return 'NO_NUMBERS', price
                else:
                    return data, price

            return 'NO_NUMBERS', price

        # Com filtro de operadoras específicas
        available_operators = get_available_operators()
        if not available_operators:
            return 'NO_NUMBERS', price

        filtered = [op for op in available_operators if op.lower() in [o.lower() for o in OPERATORS]]
        if not filtered:
            return 'NO_NUMBERS', price

        for operator in filtered:
            url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={SERVICE}&country={COUNTRY_CODE}&operator={operator}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.text.strip()
                if data.startswith('ACCESS_NUMBER'):
                    parts = data.split(':')
                    number_id = parts[1].strip() if len(parts) > 1 else ''
                    operator_info[number_id] = operator.upper()
                    logger.info(f"✓ Número obtido (Operadora: {operator.upper()})")
                    return data, price
                elif 'NO_NUMBERS' in data:
                    continue
                elif 'NO_BALANCE' in data:
                    return 'NO_BALANCE', price
                elif 'BAD_KEY' in data:
                    return 'BAD_KEY', price

        return 'NO_NUMBERS', price

    except Exception as e:
        logger.error(f"Erro ao obter número: {e}")
        return 'NO_NUMBER', "$0.00"


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
    """Solicita reenvio de SMS (status=3)"""
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


# ================= FUNÇÕES DE EMAIL (mantidas, mas não usadas) =================
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
        data, price = get_number()

        if data.startswith('ACCESS_NUMBER'):
            parts = data.split(':', 2)
            number_id = parts[1].strip()
            phone_number = parts[2].strip()

            op = operator_info.get(number_id, 'AUTO')

            setup_timeout(number_id)
            active_numbers[number_id] = {
                'phone_number': phone_number,
                'operator': op,
                'price': price,
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
                'message': f'Número obtido com sucesso'
            })
        else:
            failed_attempts[time.time()] = datetime.now()

            msg_map = {
                'NO_BALANCE': 'Saldo insuficiente!',
                'NO_NUMBERS': 'Sem números disponíveis',
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
            
            # 👇 EXTRAI APENAS O CÓDIGO NUMÉRICO
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
        'country': COUNTRY_CODE,
        'service': SERVICE,
        'operators_filter': OPERATORS,
        'successful_numbers': len(successful_numbers),
        'active_numbers': len(active_numbers),
        'total_codes': sum(len(num.get('received_codes', [])) for num in active_numbers.values()),
        'current_price': get_service_price()
    })


if __name__ == '__main__':
    logger.info("🚀 Servidor SMS iniciado (HeroSMS)")
    logger.info(f"🌎 País: Colômbia ({COUNTRY_CODE})")
    logger.info(f"📦 Serviço: {SERVICE} (Any Other)")
    logger.info(f"📱 Operadoras: TODAS (filtro desativado)")
    logger.info("⏰ Timeout: 120s")
    logger.info("✂️  Extração automática de código ativada")
    app.run(debug=True, port=3000, host='0.0.0.0')
