from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
import time
from threading import Timer, Thread
import logging
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Configuração
API_KEY = os.environ.get('API_KEY_SMS', '')
COUNTRY_CODE = 73  # Brasil
SERVICE = 'mm'
TIMEOUT_DURATION = 120  # segundos

# Controle de bloqueio - EVITA CANCELAMENTOS EXCESSIVOS
failed_attempts = {}
MAX_FAILURES_BEFORE_COOLDOWN = 3
COOLDOWN_MINUTES = 30

# Armazenamento em memória
number_timeouts = {}
active_numbers = {}
successful_numbers = set()

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
    """Obtém a lista de operadoras disponíveis para o Brasil (apenas informativo)"""
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getOperators&country={COUNTRY_CODE}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country_operators = data.get('countryOperators', {})
                operators = country_operators.get(str(COUNTRY_CODE), [])
                logger.info(f"Operadoras disponíveis no Brasil: {operators}")
                return operators
        return []
    except Exception as e:
        logger.error(f"Erro ao obter operadoras: {e}")
        return []


def identify_operator(number_id):
    """Tenta identificar a operadora de um número já obtido"""
    try:
        # Método 1: Tenta verificar no status da ativação
        url = f"{BASE_URL}?api_key={API_KEY}&action=getStatus&id={number_id}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.text.strip()
            # Algumas APIs retornam info da operadora no status
            if 'operator=' in data.lower():
                op_match = data.lower().split('operator=')[1].split('&')[0]
                return op_match.upper()
        
        # Método 2: Consulta a lista de operadoras disponíveis
        available_operators = get_available_operators()
        
        if available_operators:
            # Se só tem uma operadora disponível, é essa
            if len(available_operators) == 1:
                return available_operators[0].upper()
            
            # Se tem TIM e/ou ARQIA, prioriza essas
            tim_arqia = [op for op in available_operators if op.lower() in ['tim', 'arqia']]
            if len(tim_arqia) == 1:
                return tim_arqia[0].upper()
            elif len(tim_arqia) > 1:
                return 'TIM/ARQIA'
            
            # Retorna a primeira disponível
            return available_operators[0].upper()
        
        # Método 3: Verifica nos números ativos se já temos info
        if number_id in active_numbers:
            stored_op = active_numbers[number_id].get('operator', '')
            if stored_op and stored_op != 'Desconhecida':
                return stored_op
        
        return 'Desconhecida'
        
    except Exception as e:
        logger.error(f"Erro ao identificar operadora: {e}")
        return 'Desconhecida'


def get_service_price():
    """Obtém o preço do serviço usando a API correta"""
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
                        formatted_price = f"R$ {price:.4f}"
                        logger.info(f"💰 Preço do serviço {SERVICE}: {formatted_price}")
                        return formatted_price
            
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and SERVICE in item:
                        service_info = item[SERVICE]
                        if isinstance(service_info, dict) and 'cost' in service_info:
                            price = float(service_info['cost'])
                            formatted_price = f"R$ {price:.4f}"
                            return formatted_price
            
            logger.warning(f"Formato de preço não reconhecido: {data}")
    except Exception as e:
        logger.error(f"Erro ao obter preço: {e}")
    
    return "R$ 0.0000"


def get_number():
    """Obtém um número SEM filtro por operadora, mas identifica qual é"""
    try:
        # Verifica se está em período de muitas falhas
        if check_failure_rate():
            logger.warning("⚠️ Período de espera para evitar bloqueio")
            return 'RATE_LIMIT', "R$ 0.0000", ''
        
        # Obtém preço real do serviço
        price = get_service_price()
        
        # Obtém número sem especificar operadora
        url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={SERVICE}&country={COUNTRY_CODE}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.text.strip()
            
            if data.startswith('ACCESS_NUMBER'):
                parts = data.split(':')
                number_id = parts[1].strip() if len(parts) > 1 else ''
                
                # Identifica a operadora do número obtido
                operator = identify_operator(number_id)
                
                logger.info(f"✓ Número obtido com sucesso (Operadora: {operator})")
                return data, price, operator
                
            elif 'NO_NUMBERS' in data:
                logger.info("✗ Sem números disponíveis")
                return 'NO_NUMBERS', price, ''
            elif 'NO_BALANCE' in data:
                logger.error("✗ Saldo insuficiente!")
                return 'NO_BALANCE', price, ''
            elif 'BAD_KEY' in data:
                logger.error("✗ API Key inválida!")
                return 'BAD_KEY', price, ''
            else:
                logger.warning(f"Resposta inesperada: {data}")
                return data, price, ''
        
        logger.info("✗ Falha ao obter número")
        return 'NO_NUMBER', price, ''
        
    except Exception as e:
        logger.error(f"Erro ao obter número: {e}")
        return 'NO_NUMBER', "R$ 0.0000", ''


def setup_timeout(number_id):
    """Configura timeout apenas para limpeza de memória (sem cancelar na API)"""
    def cleanup_memory():
        try:
            if number_id in number_timeouts:
                del number_timeouts[number_id]
            if number_id in active_numbers:
                del active_numbers[number_id]
            logger.info(f"⏰ Limpeza de memória para {number_id} (sem cancelar API)")
        except Exception as e:
            logger.error(f"Erro na limpeza: {e}")
    
    timer = Timer(TIMEOUT_DURATION, cleanup_memory)
    timer.start()
    number_timeouts[number_id] = timer
    return timer


# Rotas da API

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_number', methods=['GET'])
def get_number_route():
    """Obtém novo número (qualquer operadora)"""
    try:
        data, price, operator = get_number()
        
        if data.startswith('ACCESS_NUMBER'):
            parts = data.split(':', 2)
            number_id = parts[1].strip()
            phone_number = parts[2].strip().replace('55', '', 1)
            
            setup_timeout(number_id)
            active_numbers[number_id] = {
                'phone_number': phone_number,
                'operator': operator,
                'price': price,
                'status': 'waiting',
                'created_at': time.time(),
                'received_codes': []
            }
            
            logger.info(f"✅ Número {phone_number} ({operator}) obtido (ID: {number_id})")
            return jsonify({
                'success': True,
                'response': data,
                'number_id': number_id,
                'phone_number': phone_number,
                'operator': operator,
                'price': price,
                'message': f'Número obtido com sucesso ({operator})'
            })
        else:
            # Registra falha
            failed_attempts[time.time()] = datetime.now()
            
            msg_map = {
                'NO_BALANCE': 'Saldo insuficiente!',
                'NO_NUMBERS': 'Sem números disponíveis',
                'NO_NUMBER': 'Falha ao obter número',
                'BAD_KEY': 'API Key inválida',
                'RATE_LIMIT': 'Aguarde - Muitas tentativas recentes'
            }
            return jsonify({
                'success': False,
                'response': data,
                'message': msg_map.get(data, 'Erro desconhecido')
            })
    except Exception as e:
        logger.error(f"Erro em /get_number: {e}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500


@app.route('/get_price/<number_id>', methods=['GET'])
def get_price(number_id):
    """Retorna o preço atualizado de um número específico"""
    try:
        if number_id in active_numbers:
            price = active_numbers[number_id].get('price', 'R$ 0.0000')
            operator = active_numbers[number_id].get('operator', '')
            return jsonify({
                'success': True,
                'number_id': number_id,
                'price': price,
                'operator': operator
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Número não encontrado'
            })
    except Exception as e:
        logger.error(f"Erro em /get_price: {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@app.route('/get_status/<number_id>', methods=['GET'])
def get_status(number_id):
    """Verifica status e obtém código se disponível - SEM CANCELAMENTO"""
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getStatus&id={number_id}"
        response = requests.get(url, timeout=10)
        data = response.text.strip()
        logger.info(f"Status check para {number_id}: {data}")

        result = {
            'success': True,
            'response': data,
            'has_code': False,
            'code': None,
            'status': 'waiting'
        }

        if data.startswith('STATUS_OK:'):
            code = data.split(':', 1)[1].strip()

            # Verificar se é um código NOVO
            if number_id in active_numbers:
                received_codes = active_numbers[number_id].get('received_codes', [])
                
                if code in received_codes:
                    logger.info(f"ℹ️ Código {code} já foi recebido para {number_id}")
                    result.update({
                        'has_code': False,
                        'code': None,
                        'status': 'waiting_new_code',
                        'message': 'Aguardando novo código...'
                    })
                    return jsonify(result)

            # CÓDIGO NOVO
            if number_id in number_timeouts:
                number_timeouts[number_id].cancel()
                del number_timeouts[number_id]

            if number_id not in successful_numbers:
                successful_numbers.add(number_id)
                logger.info(f"✅ Primeiro código recebido para {number_id}")

            # Armazenar código
            if number_id in active_numbers:
                active_numbers[number_id]['received_codes'].append(code)
                active_numbers[number_id]['last_code'] = code
                active_numbers[number_id]['status'] = 'code_received'

            # Pedir novo SMS (apenas retry, não cancela)
            try:
                retry_url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&status=3&id={number_id}"
                retry_resp = requests.get(retry_url, timeout=5)
                logger.info(f"🔄 Novo SMS solicitado: {retry_resp.text.strip()}")
            except Exception as e:
                logger.error(f"Erro ao solicitar novo SMS: {e}")

            logger.info(f"✅ Código recebido para {number_id}: {code}")
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
                'message': 'Número expirado ou cancelado',
                'status': 'cancelled'
            })
            # Apenas remove da memória, NÃO cancela na API
            active_numbers.pop(number_id, None)

        else:
            result.update({
                'message': data,
                'status': 'unknown'
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro em /get_status: {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'success': True,
        'successful_numbers': len(successful_numbers),
        'active_numbers': len(active_numbers),
        'total_codes': sum(len(num.get('received_codes', [])) for num in active_numbers.values()),
        'current_price': get_service_price(),
        'available_operators': get_available_operators()
    })


if __name__ == '__main__':
    logger.info("🚀 Servidor SMS iniciado (HeroSMS)")
    logger.info("📞 Números brasileiros (73) - Serviço: mm")
    logger.info("📱 Qualquer operadora disponível")
    logger.info("⏰ Timeout: 120s (sem cancelamento automático)")
    logger.info("🛡️ Proteção contra bloqueio ativada")
    print("\n" + "="*50)
    app.run(debug=True, port=3000, host='0.0.0.0')
