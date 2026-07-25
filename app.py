from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
import time
from threading import Timer, Thread
import logging
import os
import re
import imaplib
import email as email_lib
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Configuração
API_KEY = os.environ.get('API_KEY_SMS', '')
COUNTRY_CODE = 73  # Brasil
SERVICE = 'mm'
TIMEOUT_DURATION = 120  # segundos
OPERATORS = ['tim', 'arqia']  # Operadoras permitidas

# Configuração do código via email (IMAP)
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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://hero-sms.com/stubs/handler_api.php"


def check_failure_rate():
    """Verifica se muitas falhas recentes (evitar bloqueio)"""
    now = datetime.now()
    recent_failures = sum(1 for t in failed_attempts.values() 
                         if (now - t).seconds < COOLDOWN_MINUTES * 60)
    
    if recent_failures >= MAX_FAILURES_BEFORE_COOLDOWN:
        logger.warning(f"⚠️ Muitas falhas recentes ({recent_failures}). Aguarde...")
        return True
    return False


def get_available_operators():
    """Obtém a lista de operadoras disponíveis para o Brasil"""
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getOperators&country={COUNTRY_CODE}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country_operators = data.get('countryOperators', {})
                operators = country_operators.get(str(COUNTRY_CODE), [])
                logger.info(f"Operadoras disponíveis: {operators}")
                return operators
        return []
    except Exception as e:
        logger.error(f"Erro ao obter operadoras: {e}")
        return []


def filter_operators(available_operators):
    """Filtra apenas operadoras TIM e ARQIA"""
    filtered = [op for op in available_operators if op.lower() in OPERATORS]
    logger.info(f"Operadoras filtradas (TIM/ARQIA): {filtered}")
    return filtered


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
                        formatted_price = f"${price:.4f}"
                        return formatted_price
            
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and SERVICE in item:
                        service_info = item[SERVICE]
                        if isinstance(service_info, dict) and 'cost' in service_info:
                            price = float(service_info['cost'])
                            formatted_price = f"${price:.4f}"
                            return formatted_price
    except Exception as e:
        logger.error(f"Erro ao obter preço: {e}")
    
    return "$0.00"


def get_number():
    """Obtém um número com filtro por operadora"""
    try:
        if check_failure_rate():
            logger.warning("⚠️ Período de espera para evitar bloqueio")
            return 'RATE_LIMIT', "$0.00"
        
        price = get_service_price()
        available_operators = get_available_operators()
        
        if not available_operators:
            return 'NO_NUMBERS', price
        
        filtered_operators = filter_operators(available_operators)
        
        if not filtered_operators:
            return 'NO_NUMBERS', price
        
        for operator in filtered_operators:
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
    """Configura timeout para limpeza de memória"""
    def cleanup_memory():
        try:
            if number_id in number_timeouts:
                del number_timeouts[number_id]
            if number_id in active_numbers:
                del active_numbers[number_id]
            if number_id in operator_info:
                del operator_info[number_id]
            logger.info(f"⏰ Limpeza de memória para {number_id}")
        except Exception as e:
            logger.error(f"Erro na limpeza: {e}")
    
    timer = Timer(TIMEOUT_DURATION, cleanup_memory)
    timer.start()
    number_timeouts[number_id] = timer
    return timer


# ---------- Funções auxiliares do código via email (IMAP) ----------

def _limpar_html(texto):
    texto = re.sub(r'<style[\s\S]*?</style>', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<script[\s\S]*?</script>', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = texto.replace('&nbsp;', ' ').replace('&amp;', '&')
    return texto


def _extrair_texto_email(msg):
    """Pega a parte text/plain se existir, senão text/html, e limpa tags."""
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


def extrair_todos_codigos(texto):
    """Extrai TODOS os códigos numéricos possíveis do texto do email."""
    codigos = []
    
    # Padrão 1: "código/codigo/code" seguido de números
    padrao1 = re.findall(r'(?:c[oó]digo|code|código|token|pin|chave)[\s\S]{0,50}?(\d{4,8})', texto, re.IGNORECASE)
    codigos.extend(padrao1)
    
    # Padrão 2: Números isolados em linhas (4-6 dígitos)
    padrao2 = re.findall(r'(?:^|\n)\s*(\d{4,6})\s*(?:\n|$)', texto, re.MULTILINE)
    codigos.extend(padrao2)
    
    # Padrão 3: Números após ":" ou "="
    padrao3 = re.findall(r'[:=]\s*(\d{4,6})\b', texto)
    codigos.extend(padrao3)
    
    # Padrão 4: Qualquer número de 4-6 dígitos (fallback)
    if not codigos:
        padrao4 = re.findall(r'\b(\d{4,6})\b', texto)
        for num in padrao4:
            if not num.startswith(('19', '20')):  # Exclui anos
                codigos.append(num)
    
    # Remove duplicatas mantendo a ordem
    codigos_unicos = []
    for codigo in codigos:
        if codigo not in codigos_unicos:
            codigos_unicos.append(codigo)
    
    return codigos_unicos


def buscar_codigo_email():
    """Busca APENAS o código mais recente do último email."""
    global ultimo_codigo_email

    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        return {'success': False, 'message': 'EMAIL não configurado.'}

    try:
        imap = imaplib.IMAP4_SSL('imap.gmail.com')
        imap.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        imap.select('INBOX')

        # Busca emails do remetente específico
        status, dados = imap.search(None, f'(FROM "{EMAIL_SENDER_FILTRO}")')
        if status != 'OK' or not dados[0]:
            imap.logout()
            return {'success': False, 'message': 'Nenhum email encontrado.'}

        ids = dados[0].split()
        # Pega APENAS o último email (mais recente)
        ultimo_id = ids[-1]
        
        status, msg_dados = imap.fetch(ultimo_id, '(RFC822)')
        imap.logout()
        
        if status != 'OK':
            return {'success': False, 'message': 'Erro ao ler email.'}

        msg = email_lib.message_from_bytes(msg_dados[0][1])
        texto = _extrair_texto_email(msg)
        
        logger.info(f'📧 Processando email mais recente')
        logger.info(f'📧 Preview: {texto[:300]}')
        
        # Extrai todos os códigos encontrados
        codigos = extrair_todos_codigos(texto)
        
        if not codigos:
            logger.warning('❌ Nenhum código encontrado no email mais recente')
            return {
                'success': False, 
                'message': 'Nenhum código encontrado.',
                'debug_preview': texto[:200]
            }
        
        # Pega o primeiro código encontrado (mais relevante)
        novo_codigo = codigos[0]
        
        logger.info(f'📧 Códigos encontrados: {codigos}')
        logger.info(f'📧 Último código entregue: {ultimo_codigo_email}')
        logger.info(f'📧 Novo código: {novo_codigo}')
        
        # Verifica se é diferente do último entregue
        if ultimo_codigo_email is not None and novo_codigo == ultimo_codigo_email:
            logger.info(f'⚠️ Código {novo_codigo} é igual ao último entregue')
            return {
                'success': False, 
                'message': 'Código repetido',
                'code': novo_codigo
            }
        
        # Atualiza o último código entregue
        ultimo_codigo_email = novo_codigo
        logger.info(f'✅ Novo código entregue: {novo_codigo}')
        
        return {
            'success': True, 
            'code': novo_codigo
        }

    except Exception as e:
        logger.error(f'Erro ao buscar código: {e}')
        return {'success': False, 'message': f'Erro: {str(e)}'}


# Rotas da API

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
            phone_number = parts[2].strip().replace('55', '', 1)
            
            op = operator_info.get(number_id, '')
            
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
                'message': f'Número {op} obtido com sucesso'
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
                'message': msg_map.get(data, 'Erro desconhecido')
            })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500


@app.route('/get_status/<number_id>', methods=['GET'])
def get_status(number_id):
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getStatus&id={number_id}"
        response = requests.get(url, timeout=10)
        data = response.text.strip()

        result = {
            'success': True,
            'has_code': False,
            'code': None,
            'status': 'waiting'
        }

        if data.startswith('STATUS_OK:'):
            code = data.split(':', 1)[1].strip()

            if number_id in active_numbers:
                received_codes = active_numbers[number_id].get('received_codes', [])
                
                if code in received_codes:
                    result.update({
                        'has_code': False,
                        'code': None,
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

            result.update({
                'has_code': True,
                'code': code,
                'status': 'received'
            })

        elif data == 'STATUS_WAIT_CODE':
            result.update({
                'message': 'Aguardando código...',
                'status': 'waiting_code'
            })

        elif data == 'STATUS_CANCEL' or data == 'STATUS_WAIT_RETRY':
            result.update({
                'message': 'Número expirado',
                'status': 'cancelled'
            })
            active_numbers.pop(number_id, None)
            operator_info.pop(number_id, None)

        else:
            result.update({
                'message': data,
                'status': 'unknown'
            })

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
        'successful_numbers': len(successful_numbers),
        'active_numbers': len(active_numbers),
        'total_codes': sum(len(num.get('received_codes', [])) for num in active_numbers.values()),
        'allowed_operators': OPERATORS,
        'current_price': get_service_price()
    })


if __name__ == '__main__':
    logger.info("🚀 Servidor SMS iniciado (HeroSMS)")
    logger.info("📞 Números brasileiros (73) - Serviço: mm")
    logger.info("📱 Operadoras: TIM e ARQIA")
    logger.info("⏰ Timeout: 120s")
    logger.info("📧 Código via email: %s", EMAIL_SENDER_FILTRO)
    app.run(debug=True, port=3000, host='0.0.0.0')
