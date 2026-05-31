from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
import time
from threading import Timer, Thread
import logging
import os

app = Flask(__name__)
CORS(app)

# Configuração
API_KEY = os.environ.get('API_KEY_SMS', '')
COUNTRY_CODE = 73  # Brasil
SERVICE = 'mm'
TIMEOUT_DURATION = 120  # segundos
OPERATORS = ['tim', 'arqia']  # Operadoras permitidas

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


def get_available_operators():
    """Obtém a lista de operadoras disponíveis"""
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getOperators"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country_operators = data.get('countryOperators', {})
                return country_operators.get(str(COUNTRY_CODE), [])
        return []
    except Exception as e:
        logger.error(f"Erro ao obter operadoras: {e}")
        return []


def filter_operators(available_operators):
    """Filtra apenas operadoras TIM e ARQIA"""
    filtered = [op for op in available_operators if op.lower() in OPERATORS]
    logger.info(f"Operadoras disponíveis: {available_operators}")
    logger.info(f"Operadoras filtradas (TIM/ARQIA): {filtered}")
    return filtered


def get_service_price_async(number_id):
    """Obtém o preço do serviço em background (não bloqueia)"""
    try:
        url = f"{BASE_URL}?api_key={API_KEY}&action=getPrices"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Tenta extrair o preço
            if str(COUNTRY_CODE) in data and SERVICE in data[str(COUNTRY_CODE)]:
                service_info = data[str(COUNTRY_CODE)][SERVICE]
                if "cost" in service_info:
                    price = float(service_info["cost"])
                    formatted_price = f"{price:.4f}"
                    
                    # Atualiza o preço do número ativo
                    if number_id in active_numbers:
                        active_numbers[number_id]['price'] = formatted_price
                        logger.info(f"💰 Preço atualizado para {number_id}: ${formatted_price}")
                    
                    return formatted_price
    except Exception as e:
        logger.error(f"Erro ao obter preço em background: {e}")
    
    return "0.0000"


def get_number():
    """Obtém um número com filtro por operadora"""
    try:
        # Primeiro, obtém as operadoras disponíveis
        available_operators = get_available_operators()
        
        if not available_operators:
            logger.warning("Não foi possível obter a lista de operadoras")
            return 'NO_NUMBERS', "0.0000"
        
        # Filtra apenas TIM e ARQIA
        filtered_operators = filter_operators(available_operators)
        
        if not filtered_operators:
            logger.warning("Nenhuma operadora TIM ou ARQIA disponível")
            return 'NO_NUMBERS', "0.0000"
        
        # Tenta obter número para cada operadora filtrada
        for operator in filtered_operators:
            url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={SERVICE}&country={COUNTRY_CODE}&operator={operator}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.text.strip()
                
                if data.startswith('ACCESS_NUMBER'):
                    logger.info(f"✓ Número obtido com sucesso (Operadora: {operator})")
                    return data, "..."  # Placeholder - será atualizado em background
                elif 'NO_NUMBERS' in data:
                    logger.info(f"✗ Sem números disponíveis para operadora {operator}")
                    continue  # Tenta próxima operadora
                elif 'NO_BALANCE' in data:
                    logger.error("✗ Saldo insuficiente!")
                    return 'NO_BALANCE', "0.0000"
                elif 'BAD_KEY' in data:
                    logger.error("✗ API Key inválida!")
                    return 'BAD_KEY', "0.0000"
                else:
                    logger.warning(f"Resposta inesperada para operadora {operator}: {data}")
                    continue
        
        # Se chegou aqui, nenhuma operadora tinha números
        logger.info("✗ Nenhum número disponível para as operadoras TIM e ARQIA")
        return 'NO_NUMBERS', "0.0000"
        
    except Exception as e:
        logger.error(f"Erro ao obter número: {e}")
        return 'NO_NUMBER', "0.0000"


def cancel_number_automatically(number_id):
    """Cancela número após timeout"""
    try:
        if number_id in number_timeouts:
            del number_timeouts[number_id]
        if number_id in active_numbers:
            del active_numbers[number_id]
        url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&status=8&id={number_id}"
        requests.get(url, timeout=5)
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
def get_number_route():
    """Obtém novo número com filtro por operadora (TIM/ARQIA)"""
    try:
        data, price = get_number()
        
        if data.startswith('ACCESS_NUMBER'):
            parts = data.split(':', 2)
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
            
            # Busca o preço em background (não bloqueia)
            Thread(target=get_service_price_async, args=(number_id,), daemon=True).start()
            
            logger.info(f"✅ Número {phone_number} obtido (ID: {number_id})")
            return jsonify({
                'success': True,
                'response': data,
                'number_id': number_id,
                'phone_number': phone_number,
                'price': price,
                'message': 'Número obtido com sucesso'
            })
        else:
            msg_map = {
                'NO_BALANCE': 'Saldo insuficiente!',
                'NO_NUMBERS': 'Sem números disponíveis para TIM/ARQIA',
                'NO_NUMBER': 'Falha ao obter número',
                'BAD_KEY': 'API Key inválida'
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
            price = active_numbers[number_id].get('price', '0.0000')
            return jsonify({
                'success': True,
                'number_id': number_id,
                'price': price
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
    """Verifica status e obtém código se disponível"""
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
                
                # Se o código já foi recebido antes, não notificar novamente
                if code in received_codes:
                    logger.info(f"ℹ️ Código {code} já foi recebido anteriormente para {number_id}")
                    result.update({
                        'has_code': False,
                        'code': None,
                        'status': 'waiting_new_code',
                        'message': 'Aguardando novo código...'
                    })
                    return jsonify(result)

            # CÓDIGO NOVO - processar normalmente
            if number_id in number_timeouts:
                number_timeouts[number_id].cancel()
                del number_timeouts[number_id]

            if number_id not in successful_numbers:
                successful_numbers.add(number_id)
                logger.info(f"✅ Primeiro código recebido para {number_id}")

            # Armazenar código NOVO
            if number_id in active_numbers:
                active_numbers[number_id]['received_codes'].append(code)
                active_numbers[number_id]['last_code'] = code
                active_numbers[number_id]['status'] = 'code_received'

            # Pedir novo SMS
            try:
                retry_url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&status=3&id={number_id}"
                retry_resp = requests.get(retry_url, timeout=5)
                logger.info(f"🔄 Novo SMS solicitado (setStatus=3): {retry_resp.text.strip()}")
            except Exception as e:
                logger.error(f"Erro ao solicitar novo SMS: {e}")

            logger.info(f"✅ NOVO código recebido para {number_id}: {code}")
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
            logger.info(f"⏳ Aguardando código para {number_id}")

        elif data == 'STATUS_CANCEL' or data == 'STATUS_WAIT_RETRY':
            result.update({
                'message': 'Número expirado ou cancelado',
                'status': 'cancelled'
            })
            logger.info(f"✗ Número {number_id} expirado/cancelado")
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


@app.route('/cancel_number/<number_id>', methods=['GET'])
def cancel_number(number_id):
    """Cancela manualmente (setStatus=8)"""
    try:
        if number_id in number_timeouts:
            number_timeouts[number_id].cancel()
            del number_timeouts[number_id]
        active_numbers.pop(number_id, None)
        successful_numbers.discard(number_id)

        url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&status=8&id={number_id}"
        response = requests.get(url, timeout=5)
        logger.info(f"✗ Número {number_id} cancelado manualmente")
        return jsonify({
            'success': True,
            'response': response.text.strip(),
            'message': 'Número cancelado'
        })
    except Exception as e:
        logger.error(f"Erro ao cancelar: {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'success': True,
        'successful_numbers': len(successful_numbers),
        'active_numbers': len(active_numbers),
        'total_codes': sum(len(num.get('received_codes', [])) for num in active_numbers.values()),
        'allowed_operators': OPERATORS
    })


if __name__ == '__main__':
    logger.info("🚀 Servidor SMS iniciado (HeroSMS)")
    logger.info("📞 Números brasileiros (73) - Serviço: mm")
    logger.info("📱 Operadoras: TIM e ARQIA")
    logger.info("⏰ Timeout: 50s")
    logger.info("⚡ Compra direta - Preço atualizado em background!")
    print("\n" + "="*50)
    app.run(debug=True, port=3000, host='0.0.0.0')
