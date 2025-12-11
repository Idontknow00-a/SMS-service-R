from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
import time
from threading import Timer
import logging
import os

app = Flask(__name__)
CORS(app)

# Configuração
API_KEY = '221176U9964a3b7615588a1447401638328f7c3'
COUNTRY_CODE = 73
SERVICE = 'mm'
TIMEOUT_DURATION = 50
COUNTRY_CODE = 73  # Brasil
SERVICE = 'mm'
TIMEOUT_DURATION = 50  # segundos

# Armazenamento em memória
number_timeouts = {}
active_numbers = {}
successful_numbers = set()  # Só números que receberam código

# Configurar logging para mostrar no Termux
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://smshub.org/stubs/handler_api.php"

def fetch_available_prices():
    """Obtém todos os preços disponíveis - VERSÃO ORIGINAL"""
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getPrices&service={SERVICE}&country={COUNTRY_CODE}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            prices_data = response.json()
            if prices_data and str(COUNTRY_CODE) in prices_data and SERVICE in prices_data[str(COUNTRY_CODE)]:
                prices = [float(price) for price in prices_data[str(COUNTRY_CODE)][SERVICE].keys()]
                return sorted(prices)
        return []
    except Exception as e:
        logger.error(f"Erro ao obter preços: {e}")
        return []

def get_cheapest_number():
    """Tenta obter um número começando do preço mais baixo"""
    prices = fetch_available_prices()
    
    for price in prices:
        try:
            url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={SERVICE}&country={COUNTRY_CODE}&price={price}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.text.strip()
                
                if data.startswith('ACCESS_NUMBER'):
                    formatted_price = f"{price:.4f}"
                    logger.info(f"✓ Número comprado por ${formatted_price}")
                    return data, formatted_price
                elif 'NO_NUMBERS' in data:
                    logger.info(f"✗ Sem números disponíveis por ${price:.4f}")
                elif 'NO_BALANCE' in data:
                    logger.error("✗ Saldo insuficiente durante compra!")
                    return 'NO_BALANCE', "0.0000"
                else:
                    logger.warning(f"Resposta inesperada: {data}")
                    
        except Exception as e:
            logger.error(f"Erro ao tentar número com preço {price}: {e}")
            continue
    
    return 'NO_NUMBER', "0.0000"
    
def cancel_number_automatically(number_id):
    """Cancela número automaticamente após timeout"""
    try:
        if number_id in number_timeouts:
            del number_timeouts[number_id]
        
        if number_id in active_numbers:
            del active_numbers[number_id]
        
        url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&status=8&id={number_id}"
        response = requests.get(url, timeout=5)
        logger.info(f"⏰ Número {number_id} cancelado automaticamente (timeout)")
    except Exception as e:
        logger.error(f"Erro ao cancelar número {number_id}: {e}")

def setup_timeout(number_id):
    """Configura timeout para cancelamento automático"""
    timer = Timer(TIMEOUT_DURATION, lambda: cancel_number_automatically(number_id))
    timer.start()
    number_timeouts[number_id] = timer
    return timer

# Rotas da API
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_number', methods=['GET'])
def get_number():
    """Obtém um novo número"""
    try:
        # ======== PRIMEIRO: VERIFICA SALDO ========
        try:
            balance_url = f"{BASE_URL}?api_key={API_KEY}&action=getBalance"
            balance_response = requests.get(balance_url, timeout=5)
            
            if balance_response.status_code == 200:
                balance_data = balance_response.text.strip()
                
                if balance_data.startswith('ACCESS_BALANCE:'):
                    balance = float(balance_data.split(':')[1])
                    logger.info(f"💰 Saldo atual: ${balance:.4f}")
                    
                    # Se saldo insuficiente (menos de 1 centavo)
                    if balance < 0.01:
                        logger.error("✗ SALDO INSUFICIENTE!")
                        return jsonify({
                            'success': False,
                            'response': 'NO_BALANCE',
                            'message': 'Saldo insuficiente!'
                        })
                elif 'NO_BALANCE' in balance_data:
                    logger.error("✗ SALDO INSUFICIENTE (NO_BALANCE)")
                    return jsonify({
                        'success': False,
                        'response': 'NO_BALANCE',
                        'message': 'Saldo insuficiente!'
                    })
                else:
                    logger.warning(f"Resposta de saldo inválida: {balance_data}")
        except Exception as e:
            logger.error(f"Erro ao verificar saldo: {e}")
            # Continua mesmo com erro na verificação de saldo (fallback)
        
        # ======== SÓ ENTÃO: TENTA OBTER NÚMERO ========
        data, price = get_cheapest_number()
        
        if data.startswith('ACCESS_NUMBER'):
            parts = data.split(':')
            if len(parts) >= 3:
                number_id = parts[1].strip()
                phone_number = parts[2].strip().replace('55', '', 1)
                
                setup_timeout(number_id)
                
                active_numbers[number_id] = {
                    'phone_number': phone_number,
                    'price': price,
                    'status': 'waiting',
                    'created_at': time.time(),
                    'received_codes': []
                }
                
                logger.info(f"✅ Número {phone_number} obtido (ID: {number_id})")
                
                return jsonify({
                    'success': True,
                    'response': data,
                    'number_id': number_id,
                    'phone_number': phone_number,
                    'price': price,
                    'message': 'Número obtido com sucesso'
                })
        
        return jsonify({
            'success': False,
            'response': data,
            'message': 'Não foi possível obter número'
        })
        
    except Exception as e:
        logger.error(f"Erro em /get_number: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
        
@app.route('/get_status/<number_id>', methods=['GET'])
def get_status(number_id):
    """Verifica status do número e obtém código se disponível"""
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
            # Código recebido
            code = data.split(':', 1)[1].strip()
            
            # Cancelar timeout
            if number_id in number_timeouts:
                number_timeouts[number_id].cancel()
                del number_timeouts[number_id]
            
            # Adicionar aos sucessos (se for primeiro código)
            if number_id not in successful_numbers:
                successful_numbers.add(number_id)
                logger.info(f"✅ Primeiro código recebido para {number_id}")
            
            # Armazenar código
            if number_id in active_numbers:
                active_numbers[number_id]['received_codes'].append(code)
                active_numbers[number_id]['status'] = 'code_received'
                active_numbers[number_id]['last_code'] = code
            
            # Solicitar novo SMS (ACCESS_RETRY_GET)
            try:
                retry_url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&status=3&id={number_id}"
                retry_response = requests.get(retry_url, timeout=5)
                logger.info(f"📱 Novo SMS solicitado (ACCESS_RETRY_GET): {retry_response.text}")
            except Exception as e:
                logger.error(f"Erro ao solicitar novo SMS: {e}")
            
            logger.info(f"✅ Código recebido para {number_id}: {code}")
            
            result['has_code'] = True
            result['code'] = code
            result['status'] = 'received'
        
        elif data == 'STATUS_WAIT_CODE':
            result['message'] = 'Aguardando código...'
            result['status'] = 'waiting_code'
            logger.info(f"⏳ Aguardando código para {number_id}")
        
        elif data == 'STATUS_CANCEL':
            result['message'] = 'Número cancelado'
            result['status'] = 'cancelled'
            logger.info(f"✗ Número {number_id} cancelado")
            
            # Remover dos ativos
            if number_id in active_numbers:
                del active_numbers[number_id]
        
        else:
            result['message'] = data
            result['status'] = 'unknown'
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro em /get_status: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao verificar status: {str(e)}'
        }), 500

@app.route('/cancel_number/<number_id>', methods=['GET'])
def cancel_number(number_id):
    """Cancela um número manualmente"""
    try:
        # Cancelar timeout se existir
        if number_id in number_timeouts:
            number_timeouts[number_id].cancel()
            del number_timeouts[number_id]
        
        # Remover de números ativos
        if number_id in active_numbers:
            del active_numbers[number_id]
        
        # Remover de sucessos se não recebeu código
        if number_id in successful_numbers:
            successful_numbers.remove(number_id)
        
        # Cancelar na API
        url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&status=8&id={number_id}"
        response = requests.get(url, timeout=5)
        
        logger.info(f"✗ Número {number_id} cancelado manualmente")
        
        return jsonify({
            'success': True,
            'response': response.text,
            'message': 'Número cancelado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro em /cancel_number: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao cancelar número: {str(e)}'
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas"""
    return jsonify({
        'success': True,
        'successful_numbers': len(successful_numbers),
        'active_numbers': len(active_numbers),
        'total_codes': sum(len(num['received_codes']) for num in active_numbers.values() if 'received_codes' in num)
    })

if __name__ == '__main__':
    logger.info("🚀 Servidor SMS iniciado na porta 3000")
    logger.info("📞 Números brasileiros (73)")
    logger.info("⏰ Timeout: 50 segundos")
    logger.info("💵 Preços em dólar com 4 dígitos")
    print("\n" + "="*50)
    app.run(debug=True, port=3000, host='0.0.0.0')
