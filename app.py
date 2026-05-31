<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMS Service + Gerador de Dados</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: system-ui, -apple-system, sans-serif; 
            background: linear-gradient(135deg, #cbd5e1 0%, #475569 100%);
            min-height: 100vh; 
            padding: 10px; 
        }
        
        .main-container {
            max-width: 500px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .section {
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.2); 
            overflow: hidden; 
        }
        
        /* SMS Section */
        .sms-section .boxes { 
            display: flex; 
            height: 85px;
        }
        
        .sms-section .box { 
            flex: 1; 
            padding: 12px;
            display: flex; 
            flex-direction: column; 
            cursor: pointer; 
            transition: all 0.2s; 
            border-bottom: 3px solid transparent; 
            position: relative; 
            min-width: 45%; 
        }
        
        .sms-section .box:first-child { 
            border-right: 1px solid #e2e8f0; 
        }
        
        .sms-section .box:hover { 
            background: #f8fafc; 
        }
        
        .sms-section .box.active { 
            border-bottom-color: #10b981; 
            background: #f0fdf4; 
        }
        
        .sms-section .box.cancelled { 
            border-bottom-color: #ef4444; 
            background: #fef2f2; 
        }
        
        .sms-section .box-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }
        
        .sms-section .label { 
            font-size: 0.7rem;
            color: #64748b; 
            text-transform: uppercase; 
            letter-spacing: 0.3px; 
            font-weight: 600; 
            white-space: nowrap; 
        }
        
        .sms-section .price {
            font-size: 0.65rem;
            color: #10b981;
            font-weight: 600;
            background: #f0fdf4;
            padding: 1px 5px;
            border-radius: 8px;
            border: 1px solid #d1fae5;
        }
        
        .sms-section .value { 
            font-size: 1.15rem;
            font-weight: 700; 
            color: #1e293b; 
            flex: 1; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            text-align: center; 
            word-break: break-all; 
            padding: 0 3px; 
            min-height: 25px;
        }
        
        .sms-section .value.empty { 
            color: #94a3b8; 
            font-size: 0.85rem;
            font-weight: 500; 
        }
        
        .sms-section .counter {
            font-size: 0.7rem;
            color: #475569;
            font-weight: 600;
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 8px;
            position: absolute;
            bottom: 8px;
            right: 8px;
        }
        
        .sms-section .copy-indicator { 
            position: absolute; 
            top: 8px;
            right: 8px;
            background: #10b981; 
            color: white; 
            padding: 2px 5px; 
            border-radius: 8px; 
            font-size: 0.6rem;
            opacity: 0; 
            transition: opacity 0.2s; 
            z-index: 2;
        }
        
        .sms-section .copy-indicator.show { 
            opacity: 1; 
        }
        
        .sms-section .status { 
            font-size: 0.65rem;
            color: #64748b; 
            display: flex; 
            align-items: center; 
            gap: 4px; 
            margin-top: 3px;
        }
        
        .sms-section .dot { 
            width: 5px;
            height: 5px;
            border-radius: 50%; 
            background: #f59e0b; 
            animation: pulse 1.5s infinite; 
        }
        
        .sms-section .dot.received { 
            background: #10b981; 
            animation: none; 
        }
        
        .sms-section .dot.cancelled { 
            background: #ef4444; 
            animation: none; 
        }
        
        /* Data Generator Section */
        .data-section {
            padding: 15px;
        }
        
        .action-buttons {
            display: flex;
            gap: 6px;
            margin-bottom: 12px;
        }
        
        .action-btn, .gender-btn {
            flex: 1;
            padding: 6px 2px;
            border: none;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }
        
        .gender-btn {
            padding: 6px 2px;
            font-size: 0.9rem;
        }
        
        .action-btn.copy-sms { 
            background: #f1f5f9; 
            color: #64748b; 
            flex: 0 0 auto;
            width: 32px;
            min-width: 32px;
            height: 32px;
            padding: 0;
            border-radius: 6px;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .action-btn.copy-sms:hover {
            background: #e2e8f0;
        }
        
        .action-btn:not(.copy-sms), .gender-btn {
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .action-btn.generate { 
            background: #64748b; 
            color: white; 
        }
        
        .action-btn.generate:hover {
            background: #475569;
        }
        
        .gender-btn.male { 
            background: #e0f2fe; 
            color: #0369a1; 
        }
        
        .gender-btn.male.active { 
            background: #0369a1; 
            color: white; 
        }
        
        .gender-btn.male:hover:not(.active) {
            background: #bae6fd;
        }
        
        .gender-btn.female { 
            background: #fce7f3; 
            color: #db2777; 
        }
        
        .gender-btn.female.active { 
            background: #db2777; 
            color: white; 
        }
        
        .gender-btn.female:hover:not(.active) {
            background: #fbcfe8;
        }
        
        .data-field {
            margin-bottom: 8px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            cursor: pointer;
            transition: all 0.2s;
            background: #f8fafc;
        }
        
        .data-field:hover {
            border-color: #e2e8f0;
            background: #f1f5f9;
        }
        
        .data-input {
            flex: 1;
            padding: 10px 12px;
            border: none;
            font-size: 0.9rem;
            background: transparent;
            color: #64748b;
            cursor: pointer;
        }
        
        .data-input:focus {
            outline: none;
            background: #ffffffaa;
        }
        
        /* Gift Section */
        .gift-section {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            margin: 10px 0;
        }
        
        .gift-input {
            width: 100%;
            padding: 10px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 0.9rem;
            margin-bottom: 8px;
            background: white;
        }
        
        .gift-input:focus {
            outline: none;
            border-color: #0ea5e9;
        }
        
        .gift-list {
            max-height: 60px;
            overflow-y: auto;
            background: white;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 8px;
            margin-bottom: 8px;
        }
        
        .gift-item {
            padding: 6px 8px;
            border-bottom: 1px solid #cbd5e1;
            font-size: 0.8rem;
            color: #64748b;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .gift-item:hover {
            background: #cbd5e1;
        }
        
        .gift-item:last-child {
            border-bottom: none;
        }
        
        .gift-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #64748b;
        }
        
        .gift-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .gift-footer-btn {
            background: #cbd5e1;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 0.8rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .gift-count {
            font-weight: 700;
            color: #64748b;
            font-size: 0.9rem;
        }
        
        /* Settings Section */
        .settings-section {
            background: #f8fafc;
            border-radius: 8px;
            padding: 12px;
            margin-top: 5px;
        }
        
        .settings-section h3 {
            font-size: 0.85rem;
            color: #64748b;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        
        .settings-row {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .settings-input {
            flex: 1;
            padding: 8px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 0.85rem;
        }
        
        .settings-btn {
            padding: 8px 12px;
            background: #64748b;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
        }
        
        .reset-btn {
            width: 100%;
            padding: 10px;
            background: #64748b;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            margin-top: 8px;
        }
        
        .notification { 
            position: fixed; 
            top: 15px; 
            right: 15px; 
            background: #10b981;
            color: white; 
            padding: 8px 14px;
            border-radius: 6px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.15); 
            opacity: 0; 
            transform: translateX(100%); 
            transition: all 0.2s; 
            font-size: 0.8rem;
            max-width: 280px; 
            z-index: 1000; 
        }
        
        .notification.show { 
            opacity: 1; 
            transform: translateX(0); 
        }
        
        .notification.error { 
            background: #ef4444; 
        }
        
        .notification.warning { 
            background: #f59e0b; 
        }
        
        @keyframes pulse { 
            0%, 100% { opacity: 1; } 
            50% { opacity: 0.5; } 
        }
        
        @media (max-width: 350px) {
            .sms-section .boxes { 
                height: 90px; 
            }
            
            .sms-section .box { 
                padding: 10px; 
            }
            
            .sms-section .value { 
                font-size: 1.1rem; 
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- SMS Section -->
        <div class="section sms-section">
            <div class="boxes">
                <div class="box" id="numberBox" onclick="getNumber()" title="Clique para obter número">
                    <div class="copy-indicator" id="numberCopy">✓</div>
                    <div class="box-header">
                        <div class="label">Número</div>
                        <div class="price" id="numberPrice"></div>
                    </div>
                    <div class="value empty" id="numberValue">Obter</div>
                    <div class="counter" id="attempts">0</div>
                    <div class="status">
                        <div class="dot"></div>
                        <span id="numberStatus">Pronto</span>
                    </div>
                </div>
                
                <div class="box" id="codeBox" onclick="getCode()" title="Clique para receber código">
                    <div class="copy-indicator" id="codeCopy">✓</div>
                    <div class="label">Código</div>
                    <div class="value empty" id="codeValue">Receber</div>
                    <div class="counter" id="successes">0</div>
                    <div class="status">
                        <div class="dot"></div>
                        <span id="codeStatus">Aguardando</span>
                    </div>
                </div>
            </div>
        <!-- Data Generator Section -->  
        <div class="section data-section">  
            <div class="action-buttons">  
                <button class="action-btn copy-sms" onclick="copyCurrentSMSNumber()" title="Copiar número atual do SMS">📋</button>  
                <button class="gender-btn male active" onclick="setGender('male')" id="maleBtn">MAS</button>  
                <button class="gender-btn female" onclick="setGender('female')" id="femaleBtn">FEM</button>  
                <button class="action-btn generate" onclick="generateData()">GERAR</button>  
            </div>
            
            <div class="data-field" onclick="copyDataField('firstName')">
                <input type="text" class="data-input" id="firstName" readonly placeholder="Nome">
            </div>
            
            <div class="data-field" onclick="copyDataField('lastName')">
                <input type="text" class="data-input" id="lastName" readonly placeholder="Sobrenome">
            </div>
            
            <div class="data-field" onclick="copyDataField('cpf')">
                <input type="text" class="data-input" id="cpf" readonly placeholder="CPF">
            </div>
            
            <div class="data-field" onclick="copyDataField('email')">
                <input type="text" class="data-input" id="email" readonly placeholder="Email">
            </div>
            
            <div class="data-field" onclick="copyDataField('birthdate')">
                <input type="text" class="data-input" id="birthdate" readonly placeholder="Data Nascimento">
            </div>
            
            <!-- Gift Section -->
            <div class="gift-section">
                <input type="text" class="gift-input" id="giftInput" 
                       placeholder="Cole o código do gift aqui (auto-salva)"
                       oninput="handleGiftInput(event)">
                <div class="gift-list" id="giftList">
                    <!-- Gift items will appear here -->
                </div>
                
                <div class="gift-footer">
                    <button class="gift-footer-btn" onclick="clearAllGifts()" title="Limpar todos os gifts">🗑️</button>
                    <div class="gift-count" id="giftCount">0</div>
                    <button class="gift-footer-btn" onclick="copyAllGifts()" title="Copiar todos os gifts">📋</button>
                </div>
            </div>
            
            <!-- Settings Section -->
            <div class="settings-section">
                <h3>Configurações</h3>
                <div class="settings-row">
                    <input type="number" class="settings-input" id="aliasNumber" placeholder="Número do alias">
                    <button class="settings-btn" onclick="setAliasNumber()">Definir</button>
                </div>
                <div class="settings-row">
                    <input type="email" class="settings-input" id="baseEmail" placeholder="seuemail@gmail.com">
                    <button class="settings-btn" onclick="setBaseEmail()">Definir</button>
                </div>
                <button class="reset-btn" onclick="resetAlias()">Resetar Alias</button>
                <button class="reset-btn" onclick="resetSMSStats()" style="margin-top: 8px; background: #64748b;">Resetar Tentativas BOT-SMS</button>
            </div>
        </div>
    </div>
    
    <!-- Notification -->
    <div class="notification" id="notification"></div>

    <script>
        // ================= SMS FUNCTIONS =================
        let smsState = {
            id: localStorage.getItem('sms_id') || '',
            number: localStorage.getItem('sms_number') || '',
            operator: localStorage.getItem('sms_operator') || '',
            price: localStorage.getItem('sms_price') || '',
            code: localStorage.getItem('sms_code') || '',
            attempts: parseInt(localStorage.getItem('sms_attempts') || '0'),
            successes: parseInt(localStorage.getItem('sms_successes') || '0'),
            loading: false,
            firstStatusCheck: localStorage.getItem('sms_first_check') === 'true' || false,
            hasReceivedCode: localStorage.getItem('sms_hasReceivedCode') === 'true' || false,
            autoCheckInterval: null
        };

        function loadSmsState() {
            if (smsState.number) {
                // Mostra número com operadora
                const displayNumber = smsState.operator ? 
                    `${smsState.number} (${smsState.operator})` : 
                    smsState.number;
                
                document.getElementById('numberValue').textContent = displayNumber;
                document.getElementById('numberBox').classList.remove('empty');
                document.getElementById('numberPrice').textContent = smsState.price || '';
                if (smsState.price) document.getElementById('numberBox').classList.add('active');
            }
            
            if (smsState.code) {
                document.getElementById('codeValue').textContent = smsState.code;
                document.getElementById('codeBox').classList.remove('empty');
                document.getElementById('codeBox').classList.add('active');
                document.getElementById('codeStatus').textContent = 'Recebido ✓';
                document.querySelector('#codeBox .dot').classList.add('received');
                smsState.hasReceivedCode = true;
            }
            
            document.getElementById('attempts').textContent = smsState.attempts;
            document.getElementById('successes').textContent = smsState.successes;
            
            smsState.hasReceivedCode = localStorage.getItem('sms_hasReceivedCode') === 'true' || false;
            
            if (smsState.id) {
                startAutoCodeCheck();
            }
        }

        function saveSmsState() {
            localStorage.setItem('sms_id', smsState.id);
            localStorage.setItem('sms_number', smsState.number);
            localStorage.setItem('sms_operator', smsState.operator);
            localStorage.setItem('sms_price', smsState.price);
            localStorage.setItem('sms_code', smsState.code);
            localStorage.setItem('sms_attempts', smsState.attempts.toString());
            localStorage.setItem('sms_successes', smsState.successes.toString());
            localStorage.setItem('sms_first_check', smsState.firstStatusCheck.toString());
            localStorage.setItem('sms_hasReceivedCode', smsState.hasReceivedCode.toString());
        }

        function notify(msg, type = 'info') {
            const notif = document.getElementById('notification');
            notif.textContent = msg;
            notif.className = `notification ${type} show`;
            setTimeout(() => notif.classList.remove('show'), 1800);
        }

        async function copy(text, type) {
            try {
                // Remove informações de preço e operadora para copiar apenas o número
                let cleanText = text;
                if (type === 'number') {
                    cleanText = text.replace(/\s*\(TIM|ARQIA\)\s*/gi, '').replace(/R\$\s*[\d.,]+\s*/, '').trim();
                }
                
                await navigator.clipboard.writeText(cleanText);
                
                const indicator = document.getElementById(type + 'Copy');
                if (indicator) {
                    indicator.classList.add('show');
                    setTimeout(() => indicator.classList.remove('show'), 800);
                }
                
                notify(`${type === 'number' ? 'Número' : 'Código'} copiado!`);
                return true;
            } catch {
                const el = document.createElement('textarea');
                let cleanText = text;
                if (type === 'number') {
                    cleanText = text.replace(/\s*\(TIM|ARQIA\)\s*/gi, '').replace(/R\$\s*[\d.,]+\s*/, '').trim();
                }
                el.value = cleanText;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                notify(`${type === 'number' ? 'Número' : 'Código'} copiado!`);
                return true;
            }
        }

        // Função para verificar código automaticamente
        async function autoCheckCode() {
            if (!smsState.id || smsState.loading) return;
            
            try {
                const response = await fetch(`/get_status/${smsState.id}`);
                const data = await response.json();
                
                if (data.success && data.has_code && data.code) {
                    // Código recebido automaticamente!
                    smsState.code = data.code;
                    smsState.successes++;
                    smsState.hasReceivedCode = true;
                    smsState.firstStatusCheck = true;
                    
                    document.getElementById('codeValue').textContent = smsState.code;
                    document.getElementById('codeBox').classList.add('active');
                    document.getElementById('codeBox').classList.remove('empty');
                    document.getElementById('codeStatus').textContent = 'Recebido ✓';
                    document.querySelector('#codeBox .dot').classList.add('received');
                    document.getElementById('successes').textContent = smsState.successes;
                    
                    saveSmsState();
                    
                    await copy(smsState.code, 'code');
                    notify(`Código recebido: ${smsState.code}`, 'info');
                }
            } catch (error) {
                // Silencia erros
            }
        }

        function startAutoCodeCheck() {
            if (smsState.autoCheckInterval) {
                clearInterval(smsState.autoCheckInterval);
            }
            // Verifica a cada 3 segundos
            smsState.autoCheckInterval = setInterval(autoCheckCode, 3000);
        }

        function stopAutoCodeCheck() {
            if (smsState.autoCheckInterval) {
                clearInterval(smsState.autoCheckInterval);
                smsState.autoCheckInterval = null;
            }
        }

        async function getNumber() {
            if (smsState.loading) return;
            
            smsState.loading = true;
            smsState.attempts++;
            smsState.firstStatusCheck = false;
            smsState.hasReceivedCode = false;
            saveSmsState();
            
            document.getElementById('attempts').textContent = smsState.attempts;
            document.getElementById('numberValue').textContent = '...';
            document.getElementById('numberStatus').textContent = 'Obtendo';
            document.getElementById('numberPrice').textContent = '';
            
            try {
                // REMOVIDO cancelamento de número anterior para evitar bloqueios
                
                const res = await fetch('/get_number');
                const data = await res.json();
                
                if (data.success) {
                    smsState.id = data.number_id;
                    smsState.number = data.phone_number;
                    smsState.operator = data.operator || '';
                    smsState.price = data.price;
                    smsState.code = '';
                    
                    // Mostra número com operadora
                    const displayNumber = data.operator ? 
                        `${data.phone_number} (${data.operator})` : 
                        data.phone_number;
                    
                    document.getElementById('numberValue').textContent = displayNumber;
                    document.getElementById('numberPrice').textContent = data.price;
                    document.getElementById('numberBox').classList.remove('empty', 'cancelled');
                    document.getElementById('numberBox').classList.add('active');
                    document.getElementById('numberStatus').textContent = 'Pronto';
                    document.querySelector('#numberBox .dot').classList.remove('cancelled');
                    
                    document.getElementById('codeValue').textContent = 'Receber';
                    document.getElementById('codeBox').classList.remove('active', 'cancelled', 'empty');
                    document.getElementById('codeStatus').textContent = 'Aguardando';
                    document.querySelector('#codeBox .dot').classList.remove('received', 'cancelled');
                    
                    saveSmsState();
                    
                    // Inicia verificação automática
                    startAutoCodeCheck();
                    
                    await copy(smsState.number, 'number');
                    notify(`Número ${data.operator || ''}: ${smsState.number} (${data.price})`);
                } else {
                    notify(data.message || 'Sem números disponíveis', 'error');
                    document.getElementById('numberValue').textContent = 'Erro';
                    document.getElementById('numberStatus').textContent = 'Erro';
                    document.getElementById('numberBox').classList.remove('active');
                    saveSmsState();
                }
            } catch (error) {
                console.error('Erro:', error);
                notify('Erro de conexão', 'error');
                document.getElementById('numberValue').textContent = 'Erro';
                document.getElementById('numberStatus').textContent = 'Erro';
                document.getElementById('numberBox').classList.remove('active');
                saveSmsState();
            } finally {
                smsState.loading = false;
            }
        }

        async function getCode() {
            if (!smsState.id || smsState.loading) {
                if (!smsState.id) notify('Obtenha um número primeiro', 'error');
                return;
            }
            
            smsState.loading = true;
            document.getElementById('codeValue').textContent = '...';
            document.getElementById('codeStatus').textContent = 'Verificando';
            document.getElementById('codeBox').classList.remove('empty');
            
            try {
                const res = await fetch(`/get_status/${smsState.id}`);
                const data = await res.json();
                
                if (data.success) {
                    if (data.has_code && data.code) {
                        // Código recebido manualmente
                        smsState.code = data.code;
                        smsState.successes++;
                        smsState.hasReceivedCode = true;
                        smsState.firstStatusCheck = true;
                        
                        document.getElementById('codeValue').textContent = smsState.code;
                        document.getElementById('codeBox').classList.add('active');
                        document.getElementById('codeBox').classList.remove('empty');
                        document.getElementById('codeStatus').textContent = 'Recebido ✓';
                        document.querySelector('#codeBox .dot').classList.add('received');
                        document.getElementById('successes').textContent = smsState.successes;
                        
                        saveSmsState();
                        
                        await copy(smsState.code, 'code');
                        notify(`Código: ${smsState.code}`, 'info');
                        
                    } else if (data.status === 'waiting_code') {
                        // Verifica se JÁ TEM CÓDIGO SALVO
                        if (smsState.code && smsState.hasReceivedCode) {
                            document.getElementById('codeValue').textContent = smsState.code;
                            document.getElementById('codeStatus').textContent = 'Recebido ✓';
                            
                            await copy(smsState.code, 'code');
                            notify(`Código atual: ${smsState.code}`, 'info');
                            
                            smsState.firstStatusCheck = true;
                            
                        } else {
                            // Ainda aguardando - NÃO CANCELA AUTOMATICAMENTE
                            document.getElementById('codeValue').textContent = 'Aguardando...';
                            document.getElementById('codeStatus').textContent = 'Aguardando SMS...';
                            notify('Aguardando SMS...', 'info');
                        }
                        
                    } else if (data.status === 'cancelled') {
                        document.getElementById('codeStatus').textContent = 'Expirado';
                        document.getElementById('codeValue').textContent = 'Expirado';
                        document.getElementById('numberBox').classList.remove('active');
                        document.getElementById('numberBox').classList.add('cancelled');
                        notify('Número expirado', 'warning');
                        
                        // Limpa estado
                        smsState.id = '';
                        smsState.code = '';
                        stopAutoCodeCheck();
                        saveSmsState();
                        
                    } else {
                        document.getElementById('codeStatus').textContent = data.message || 'Status';
                        document.getElementById('codeValue').textContent = smsState.code || '...';
                        notify(data.message || 'Status', 'info');
                    }
                } else {
                    notify(data.message || 'Erro ao verificar', 'error');
                    document.getElementById('codeStatus').textContent = 'Erro';
                    document.getElementById('codeValue').textContent = smsState.code || 'Erro';
                }
            } catch (error) {
                notify('Erro de conexão', 'error');
                document.getElementById('codeStatus').textContent = 'Erro';
                document.getElementById('codeValue').textContent = smsState.code || 'Erro';
            } finally {
                smsState.loading = false;
                saveSmsState();
            }
        }

        // ================= DATA GENERATOR FUNCTIONS =================
        const maleNames = ["Abelardo", "Adriano", "Agnaldo", "Alan", "Alberto", "Aldo", "Alex", "Alexandre", "Alfredo", "Alvaro",
            "Anderson", "Andre", "Antonio", "Ariel", "Augusto", "Aureliano", "Bruno", "Caio", "Cassio",
            "Cesar", "Cristiano", "Daniel", "Davi", "Diego", "Douglas", "Eduardo", "Elias", "Emilio", "Enzo",
            "Felipe", "Fernando", "Francisco", "Gabriel", "Gustavo", "Henrique", "Hugo", "Igor", "Ivo", "Jackson",
            "Jair", "James", "Jander", "Joao", "Jorge", "Jose", "Juan", "Julio", "Junior", "Kaio", "Leonardo",
            "Leandro", "Luis", "Luciano", "Lucas", "Marcelo", "Marcos", "Mario", "Martin", "Matheus", "Mauricio",
            "Miguel", "Moises", "Nicolas", "Nilton", "Nivaldo", "Otavio", "Paulo", "Pedro", "Rafael", "Renato", "Ricardo",
            "Roberto", "Rogerio", "Romulo", "Ronaldo", "Rodrigo", "Samuel", "Sergio", "Silvio", "Thales", "Tiago",
            "Tobias", "Tomas", "Vagner", "Vitor", "Vinicius", "Wagner", "Wallace", "Washington", "Willian", "Wilson",
            "Walter", "Ademir", "Adolfo", "Agostinho", "Ailton", "Alcides", "Alfredo", "Altair", "Amadeu", "Americo",
            "Anselmo", "Antonino", "Arnaldo", "Artur", "Aurelio", "Bento", "Benjamim", "Benicio", "Bernard",
            "Brendon", "Caetano", "Carlos", "Carmelo", "Cassio", "Celso", "Claudinei", "Claudemir", "Claudio",
            "Cleo", "Cristiano", "Damiao", "Danilo", "Dario", "Edgard", "Edilson", "Edson", "Efraim", "Eike",
            "Eliseu", "Emiliano", "Enrico", "Epitacio", "Erico", "Eugenio", "Evaldo", "Evandro", "Everaldo", "Fabiano",
            "Fabricio", "Fabio", "Feliciano", "Filomeno", "Flavio", "Florencio", "Frederico", "Geraldo", "Gideon",
            "Gilberto", "Giordano", "Giovani", "Gregorio", "Heitor", "Icaro", "Ilson", "Ismael", "Israel", "Italo",
            "Jaime", "Joaquim", "Jose Maria", "Josuel", "Joviano", "Luan", "Luiz Felipe", "Marcio", "Marco", "Nelio",
            "Nestor", "Nilson", "Norberto", "Nuno", "Osmar", "Paulo", "Plinio", "Rubens", "Ruy", "Salomao",
            "Samir", "Sandro", "Severino", "Sidnei", "Silvano", "Silvio", "Tadeu", "Tarcisio", "Teodoro", "Thiago", "Tomas",
            "Ulysses", "Urbano", "Valdir", "Valter", "Vicente", "Vladmir", "Waldemar", "Wilmar", "Wladimir"];
            
        const femaleNames = ["Abigail", "Adelaide", "Adelia", "Adriana", "Agatha", "Agnes", "Aida", "Aileen", "Aira", "Alana", "Alice", "Aline", "Alzira", "Amalia", "Amanda", "Amelia", "Ana", "Analia", "Andrea", "Andressa", "Angela", "Angelica", "Anita", "Antonia", "Aparecida", "Ariana", "Ariane", "Arlete", "Arya", "Aurora", "Barbara", "Beatriz", "Benedita", "Berenice", "Bernadete", "Bianca", "Bruna", "Brunilda", "Caetana", "Camila", "Carina", "Carla", "Carmem", "Carmo", "Carolina", "Cassia", "Catarina", "Cecilia", "Celina", "Celia", "Clara", "Clarice", "Clarinda", "Claudia", "Clementina", "Cleonice", "Clotilde", "Conceicao", "Constancia", "Cristina", "Dafne", "Dalva", "Daniela", "Daphne", "Dara", "Debora", "Deise", "Denise", "Diana", "Dilma", "Diolinda", "Diva", "Dora", "Doroteia", "Eduarda", "Elaine", "Eliana", "Elisabete", "Elisabeth", "Elisa", "Elisete", "Elizangela", "Elsa", "Elza", "Emanuela", "Emilia", "Emily", "Eneida", "Ercilia", "Erica", "Ermelinda", "Ester", "Esther", "Eunice", "Eva", "Evelyn", "Fabiana", "Fabiola", "Fatima", "Felicia", "Fernanda", "Filomena", "Flavia", "Francisca", "Gabriela", "Gabrielle", "Geralda", "Gertrudes", "Giovanna", "Giselle", "Gloria", "Graca", "Graciela", "Graziella", "Guadalupe", "Helena", "Heloisa", "Henriqueta", "Hilda", "Idalina", "Idalia", "Idalina", "Ieda", "Ileana", "Ilma", "Ilona", "Ines", "Iolanda", "Ione", "Irene", "Iris", "Isabel", "Isabela", "Isis", "Ivana", "Ivone", "Jacinta", "Janaina", "Janete", "Janice", "Jasmin", "Jeane", "Jocasta", "Joceline", "Joana", "Jordana", "Josefa", "Josefina", "Jovita", "Judite", "Julia", "Juliana", "Julieta", "Jurema", "Justina", "Karla", "Karoline", "Katharina", "Katia", "Katrina", "Kelly", "Kim", "Lais", "Lara", "Laura", "Laurinda", "Leandra", "Leila", "Lena", "Leonor", "Leticia", "Lia", "Liana", "Lilian", "Liliana", "Linda", "Lineia", "Livia", "Loren", "Lorena", "Luana", "Lucia", "Luciana", "Luciene", "Lucrecia", "Ludmila", "Luisa", "Luzia", "Madalena", "Magda", "Magnolia", "Maia", "Maira", "Manuela", "Mara", "Marcela", "Marcia", "Marcilia", "Margarida", "Maria", "Mariana", "Marilda", "Marina", "Marisa", "Marlene", "Marta", "Matilde", "Maura", "Mavi", "Maxima", "Mayara", "Maysa", "Melania", "Melinda", "Melissa", "Mercedes", "Milena", "Miriam", "Mirian", "Mirela", "Miriam", "Monica", "Nadia", "Nair", "Nancy", "Nara", "Natividade", "Natalia", "Natasha", "Nazare", "Nela", "Nelia", "Nely", "Nereida", "Neyde", "Neuza", "Nidia", "Nila", "Nilza", "Nina", "Ninfa", "Nisia", "Noemia", "Noemi", "Norma", "Nubia", "Odalicia", "Odete", "Ofelia", "Olga", "Olimpia", "Otilia", "Palmira", "Patricia", "Paula", "Paulina", "Pauline", "Penelope", "Perpetua", "Piedade", "Pilar", "Priscila", "Querina", "Quintina", "Rafaela", "Raquel", "Rebeca", "Regina", "Renata", "Rita", "Roberta", "Rosa", "Rosalina", "Rosana", "Rosangela", "Rosario", "Rosilene", "Rosimeire", "Rubia", "Rute", "Sabrina", "Samanta", "Sandra", "Sara", "Sasha", "Selena", "Selma", "Severina", "Sheila", "Sibila", "Sibila", "Silvana", "Silvia", "Simone", "Sofia", "Solange", "Sonia", "Soraya", "Suellen", "Sulamita", "Suzana", "Tania", "Tassia", "Tatiana", "Telma", "Teresa", "Tereza", "Thereza", "Tiana", "Tina", "Tirza", "Tomasia", "Valeria", "Valesca", "Valquiria", "Vanessa", "Vanda", "Verena", "Veridiana", "Veronica", "Victoria", "Vilma", "Violeta", "Virginia", "Vitoria", "Vivian", "Viviane", "Wanda", "Xenia", "Yara", "Yasmin", "Yeda", "Yolanda", "Yone", "Yvone", "Zaira", "Zelia", "Zenaide", "Zenilda", "Zilda"];
            
        const lastNames = ["Abreu", "Albuquerque", "Almeida", "Andrade", "Araujo", "Barbosa", "Barros", "Borges", "Brandao", "Brazil",
            "Campos", "Carvalho", "Castro", "Chaves", "Clemente", "Costa", "Cruz", "Dias", "Duarte", "Faria",
            "Fernandes", "Ferreira", "Freitas", "Gama", "Garcia", "Goncalves", "Gomes", "Goncalves", "Guimaraes",
            "Henrique", "Lima", "Lopes", "Lourenco", "Macedo", "Machado", "Martins", "Melo", "Mesquita", "Miranda",
            "Moraes", "Moreira", "Mota", "Neto", "Oliveira", "Pereira", "Pinto", "Rezende", "Ribeiro", "Rodrigues",
            "Romero", "Rosa", "Santos", "Silva", "Silveira", "Siqueira", "Souza", "Teixeira", "Torres", "Valente",
            "Vargas", "Vieira", "Vila", "Vieira", "Araujo", "Alves", "Bezerra", "Campos", "Cardoso", "Castro",
            "Cruz", "Dantas", "Falcao", "Ferreira", "Freitas", "Goncalves", "Gomes", "Guimaraes", "Lima", "Lopes",
            "Melo", "Mendes", "Moraes", "Moreira", "Mota", "Oliveira", "Pacheco", "Pereira", "Pinto", "Reis",
            "Ribeiro", "Rodrigues", "Santos", "Silva", "Silveira", "Siqueira", "Souza", "Teixeira", "Torres", "Valente",
            "Vargas", "Vieira", "Vila", "Viana", "Antunes", "Araujo", "Albuquerque", "Almeida", "Barbosa", "Barros",
            "Brandao", "Brazil", "Campos", "Carvalho", "Castro", "Chaves", "Clemente", "Costa", "Cruz", "Dias",
            "Duarte", "Faria", "Fernandes", "Ferreira", "Freitas", "Gama", "Garcia", "Goncalves", "Gomes", "Guimaraes",
            "Henrique", "Lima", "Lopes", "Lourenco", "Macedo", "Machado", "Martins", "Melo", "Mesquita", "Miranda",
            "Moraes", "Moreira", "Mota", "Neto", "Oliveira", "Pereira", "Pinto", "Rezende", "Ribeiro", "Rodrigues",
            "Romero", "Rosa", "Santos", "Silva", "Silveira", "Siqueira", "Souza", "Teixeira", "Torres", "Valente",
            "Vargas", "Vieira", "Vila", "Vieira", "Araujo", "Alves", "Bezerra", "Campos", "Cardoso", "Castro",
            "Cruz", "Dantas", "Falcao", "Ferreira", "Freitas", "Goncalves", "Gomes", "Guimaraes", "Lima", "Lopes",
            "Melo", "Mendes", "Moraes", "Moreira", "Mota", "Oliveira", "Pacheco", "Pereira", "Pinto", "Reis",
            "Ribeiro", "Rodrigues", "Santos", "Silva", "Silveira", "Siqueira", "Souza", "Teixeira", "Torres", "Valente",
            "Vargas", "Vieira", "Vila", "Viana", "Antunes", "Barros", "Carvalho", "Castro", "Cavalcante", "Chaves",
            "Costa", "Cruz", "Dias", "Duarte", "Ferreira", "Freitas", "Gomes", "Goncalves", "Guimaraes", "Lima",
            "Lopes", "Machado", "Mendes", "Melo", "Moraes", "Moreira", "Neto", "Oliveira", "Pereira", "Pinto",
            "Reis", "Ribeiro", "Rodrigues", "Silva", "Silveira", "Siqueira", "Souza", "Teixeira", "Torres", "Valente"];
        
        let currentGender = localStorage.getItem('currentGender') || 'male';
        let currentData = JSON.parse(localStorage.getItem('currentData')) || null;
        let gifts = JSON.parse(localStorage.getItem('gifts')) || [];

        function setGender(gender) {
            currentGender = gender;
            localStorage.setItem('currentGender', gender);
            document.getElementById('maleBtn').classList.toggle('active', gender === 'male');
            document.getElementById('femaleBtn').classList.toggle('active', gender === 'female');
        }
        
        function generateCPF() {
            let cpf = '';
            for (let i = 0; i < 9; i++) cpf += Math.floor(Math.random() * 10);
            
            let sum = 0;
            for (let i = 0; i < 9; i++) sum += parseInt(cpf[i]) * (10 - i);
            let digit1 = 11 - (sum % 11);
            if (digit1 > 9) digit1 = 0;
            cpf += digit1;
            
            sum = 0;
            for (let i = 0; i < 10; i++) sum += parseInt(cpf[i]) * (11 - i);
            let digit2 = 11 - (sum % 11);
            if (digit2 > 9) digit2 = 0;
            cpf += digit2;
            
            return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1$2$3$4');
        }
        
        function generateBirthdate() {
            const date = new Date(1950 + Math.floor(Math.random() * 53), Math.floor(Math.random() * 12), 1 + Math.floor(Math.random() * 28));
            const day = ('0' + date.getDate()).slice(-2);
            const month = ('0' + (date.getMonth() + 1)).slice(-2);
            const year = date.getFullYear();
            return day + month + year;
        }
        
        function generateEmail(isNewGeneration = true) {
            let alias = parseInt(localStorage.getItem('aliasNumber')) || 1;
            const base = localStorage.getItem('baseEmail') || "teste@gmail.com";
            
            if (isNewGeneration) {
                const email = base.split('@')[0] + '+' + alias + '@' + base.split('@')[1];
                localStorage.setItem('aliasNumber', alias + 1);
                return email;
            } else {
                return base.split('@')[0] + '+' + alias + '@' + base.split('@')[1];
            }
        }
        
        function generateData() {
            const firstNames = currentGender === 'male' ? maleNames : femaleNames;
            const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
            const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
            
            const newData = {
                firstName: firstName,
                lastName: lastName,
                cpf: generateCPF(),
                email: generateEmail(true),
                birthdate: generateBirthdate()
            };
            
            currentData = newData;
            localStorage.setItem('currentData', JSON.stringify(newData));
            
            document.getElementById('firstName').value = newData.firstName;
            document.getElementById('lastName').value = newData.lastName;
            document.getElementById('cpf').value = newData.cpf;
            document.getElementById('email').value = newData.email;
            document.getElementById('birthdate').value = newData.birthdate;
            
            // Atualiza o número do alias no campo
            const alias = parseInt(localStorage.getItem('aliasNumber')) || 1;
            document.getElementById('aliasNumber').value = alias;
            
            notify('Sucesso!');
        }

        function generateDataOnLoad() {
            const firstNames = currentGender === 'male' ? maleNames : femaleNames;
            const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
            const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
            
            const newData = {
                firstName: firstName,
                lastName: lastName,
                cpf: generateCPF(),
                email: generateEmail(false),
                birthdate: generateBirthdate()
            };
            
            currentData = newData;
            localStorage.setItem('currentData', JSON.stringify(newData));
            
            document.getElementById('firstName').value = newData.firstName;
            document.getElementById('lastName').value = newData.lastName;
            document.getElementById('cpf').value = newData.cpf;
            document.getElementById('email').value = newData.email;
            document.getElementById('birthdate').value = newData.birthdate;
        }

        function loadSavedData() {
            if (currentData) {
                document.getElementById('firstName').value = currentData.firstName;
                document.getElementById('lastName').value = currentData.lastName;
                document.getElementById('cpf').value = currentData.cpf;
                document.getElementById('email').value = currentData.email;
                document.getElementById('birthdate').value = currentData.birthdate;
            } else {
                generateDataOnLoad();
            }
        }
        
        function copyDataField(fieldId) {
            const field = document.getElementById(fieldId);
            const text = field.value;
            
            if (!text || text === '-' || text === 'Clique em Gerar') {
                notify('Nenhum dado para copiar', 'warning');
                return;
            }
            
            navigator.clipboard.writeText(text).then(() => {
                notify('Copiado!');
            }).catch(() => {
                const el = document.createElement('textarea');
                el.value = text;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                notify('Copiado!');
            });
        }
        
        // Função para copiar número do SMS (apenas números, sem operadora)
        function copyCurrentSMSNumber() {
            if (!smsState.number || smsState.number === 'Obter' || smsState.number === '...' || smsState.number === 'Erro') {
                notify('Nenhum número SMS disponível', 'error');
                return;
            }
            
            // Remove informações de operadora e preço
            const cleanNumber = smsState.number.replace(/\s*\(TIM|ARQIA\)\s*/gi, '').trim();
            
            navigator.clipboard.writeText(cleanNumber).then(() => {
                notify(`Núm copiado`);
            }).catch(() => {
                const el = document.createElement('textarea');
                el.value = cleanNumber;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                notify(`Núm copiado`);
            });
        }
        
        function setAliasNumber() {
            const number = document.getElementById('aliasNumber').value;
            if (number) {
                localStorage.setItem('aliasNumber', number);
                notify('Número definido: ' + number);
            }
        }
        
        function setBaseEmail() {
            const email = document.getElementById('baseEmail').value;
            if (email && email.includes('@')) {
                localStorage.setItem('baseEmail', email);
                notify('Email base definido');
            }
        }
        
        function resetAlias() {
            localStorage.removeItem('aliasNumber');
            notify('Alias resetado');
        }

        // ================= GIFT FUNCTIONS =================
function handleGiftInput(event) {
    const giftInput = document.getElementById('giftInput');
    const giftCode = giftInput.value.trim();
    
    // Verifica apenas se tem conteúdo mínimo (reduzido para 3 caracteres)
    if (giftCode.length < 3) return;
    
    // Verifica se o texto colado parece um código (mais flexível)
    // Aceita: letras, números, hífens, underscores, e códigos como "ABCD-1234"
    const looksLikeCode = /^[A-Za-z0-9\-_]+$/.test(giftCode) || 
                         giftCode.includes('-') || 
                         giftCode.includes('_') ||
                         giftCode.length >= 6; // Qualquer coisa com 6+ caracteres
    
    if (!looksLikeCode) return;
    
    // Limpa timer anterior e configura novo
    clearTimeout(giftInput.timer);
    giftInput.timer = setTimeout(() => {
        // Verifica se não é o mesmo código que já está sendo processado
        if (giftCode && giftCode.length >= 3) {
            addGiftToCollection(giftCode);
            giftInput.value = ''; // Limpa o campo
        }
    }, 500); // Reduzido para 500ms para resposta mais rápida
}

function addGiftToCollection(giftCode) {
    // Verificações mais flexíveis
    if (!currentData || !currentData.email) {
        notify('Gere dados primeiro!', 'warning');
        return false;
    }
    
    if (!smsState.number || smsState.number === 'Obter' || smsState.number === '...' || smsState.number === 'Erro') {
        notify('Obtenha um número primeiro!', 'warning');
        return false;
    }
    
    // Verifica se já existe este gift (case insensitive)
    if (gifts.some(g => g.code.toLowerCase() === giftCode.toLowerCase())) {
        notify('Este gift já foi adicionado!', 'warning');
        return false;
    }
    
    const gift = {
        code: giftCode,
        number: smsState.number,
        operator: smsState.operator || '',
        email: currentData.email,
        timestamp: new Date().toLocaleTimeString('pt-BR', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        })
    };
    
    gifts.unshift(gift);
    
    // Salva no localStorage
    localStorage.setItem('gifts', JSON.stringify(gifts));
    
    // Atualiza a lista visual
    updateGiftList();
    
    notify(`✓ Gift adicionado! Total: ${gifts.length}`);
    console.log('Gift adicionado:', gift); // Debug
    
    return true;
}

// Adicione também um evento de paste (colar) como backup
document.addEventListener('DOMContentLoaded', function() {
    const giftInput = document.getElementById('giftInput');
    if (giftInput) {
        // Evento de colar (CTRL+V)
        giftInput.addEventListener('paste', function(e) {
            // Pequeno delay para pegar o valor colado
            setTimeout(() => {
                const value = giftInput.value.trim();
                if (value.length >= 3) {
                    handleGiftInput({ target: giftInput });
                }
            }, 100);
        });
        
        // Evento de blur (quando sai do campo) como backup
        giftInput.addEventListener('blur', function() {
            const value = giftInput.value.trim();
            if (value.length >= 3 && !gifts.some(g => g.code === value)) {
                handleGiftInput({ target: giftInput });
            }
        });
    }
});

        function updateGiftList() {
    const giftList = document.getElementById('giftList');
    const giftCount = document.getElementById('giftCount');
    
    if (!giftList || !giftCount) {
        console.error('Elementos da lista de gifts não encontrados');
        return;
    }
    
    giftCount.textContent = gifts.length;
    
    if (gifts.length === 0) {
        giftList.innerHTML = '<div class="gift-item" style="color: #475569; text-align: center; font-style: italic;">Nenhum gift adicionado ainda</div>';
        return;
    }
    
    giftList.innerHTML = '';
    
    // Mostra até 5 gifts recentes (aumentado de 3 para 5)
    const recentGifts = gifts.slice(0, 5);
    
    recentGifts.forEach((gift) => {
        const item = document.createElement('div');
        item.className = 'gift-item';
        item.onclick = () => copySingleGift(gift);
        item.style.cursor = 'pointer';
        
        // Mostra informações resumidas
        const shortCode = gift.code.length > 15 ? gift.code.substring(0, 15) + '...' : gift.code;
        const shortNumber = gift.number.length > 10 ? gift.number.substring(0, 10) + '...' : gift.number;
        
        item.innerHTML = `
            <div style="font-weight: 600; color: #1e293b; margin-bottom: 3px; font-size: 0.85rem;">
                ${shortCode}
            </div>
            <div class="gift-info" style="font-size: 0.7rem;">
                <span title="${gift.number} ${gift.operator}">📱 ${shortNumber}</span>
                <span title="${gift.email}">📧 ${gift.email.split('@')[0].substring(0, 8)}...</span>
                <span>🕐 ${gift.timestamp}</span>
            </div>
        `;
        
        item.title = `Clique para copiar: ${gift.code}\nNúmero: ${gift.number} ${gift.operator}\nEmail: ${gift.email}`;
        giftList.appendChild(item);
    });
    
    // Se tiver mais gifts, mostra indicador
    if (gifts.length > 5) {
        const moreItem = document.createElement('div');
        moreItem.className = 'gift-item';
        moreItem.style.textAlign = 'center';
        moreItem.style.color = '#64748b';
        moreItem.style.fontStyle = 'italic';
        moreItem.style.fontSize = '0.75rem';
        moreItem.style.padding = '8px';
        moreItem.style.background = '#f1f5f9';
        moreItem.style.cursor = 'pointer';
        moreItem.textContent = `📋 Ver todos os ${gifts.length} gifts`;
        moreItem.onclick = () => showAllGifts();
        giftList.appendChild(moreItem);
    }
    
    console.log(`Lista de gifts atualizada: ${gifts.length} items`); // Debug
}

        function showAllGifts() {
            if (gifts.length === 0) return;
            
            let message = `=== TODOS OS GIFTS (${gifts.length}) ===\n\n`;
            
            gifts.forEach((gift, index) => {
                message += `Gift #${index + 1}:\n`;
                message += `Código: ${gift.code}\n`;
                message += `Número: ${gift.number} ${gift.operator}\n`;
                message += `Email: ${gift.email}\n`;
                message += `Horário: ${gift.timestamp}\n\n`;
            });
            
            alert(message);
        }

        function copySingleGift(gift) {
            const text = `${gift.code}`;
            
            navigator.clipboard.writeText(text).then(() => {
                notify('Gift copiado!');
            }).catch(() => {
                const el = document.createElement('textarea');
                el.value = text;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                notify('Gift copiado!');
            });
        }

        function copyAllGifts() {
            if (gifts.length === 0) {
                notify('Nenhum gift para copiar', 'warning');
                return;
            }
            
            let text = `=== Lista de GIFTS e CONTAS ===\n\n`;
            
            gifts.forEach((gift, index) => {
                text += `${gift.code}\n`;
                text += `${gift.number}\n`;
                text += `${gift.email}\n`;
                text += `${gift.timestamp}\n`;
                
                if (index < gifts.length - 1) {
                    text += '\n';
                }
            });
            
            navigator.clipboard.writeText(text).then(() => {
                notify(`✓ ${gifts.length} gifts copiados!`);
            }).catch(() => {
                const el = document.createElement('textarea');
                el.value = text;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                notify(`✓ ${gifts.length} gifts copiados!`);
            });
        }
        
        function clearAllGifts() {
            if (gifts.length === 0) {
                notify('Nenhum gift para limpar', 'warning');
                return;
            }
            
            const count = gifts.length;
            gifts = [];
            localStorage.setItem('gifts', JSON.stringify(gifts));
            updateGiftList();
            notify(`✓ ${count} gifts removidos`);
        }
        
        // Função para resetar stats do SMS
        function resetSMSStats() {
            smsState.attempts = 0;
            smsState.successes = 0;
            
            document.getElementById('attempts').textContent = '0';
            document.getElementById('successes').textContent = '0';
            
            localStorage.setItem('sms_attempts', '0');
            localStorage.setItem('sms_successes', '0');
            
            notify('✓ Contadores resetados');
        }

        // ================= INITIALIZATION =================
function init() {
    // SMS
    loadSmsState();
    
    // Data Generator
    setGender(currentGender);
    loadSavedData();
    
    const savedAlias = localStorage.getItem('aliasNumber');
    const savedBaseEmail = localStorage.getItem('baseEmail');
    
    if (savedAlias) {
        document.getElementById('aliasNumber').value = savedAlias;
    }
    if (savedBaseEmail) {
        document.getElementById('baseEmail').value = savedBaseEmail;
    }
    
    // Gifts
    updateGiftList();
    
    // Configurar eventos do gift input
    const giftInput = document.getElementById('giftInput');
    if (giftInput) {
        // Remove eventos antigos para não duplicar
        giftInput.removeEventListener('paste', handlePaste);
        giftInput.removeEventListener('blur', handleBlur);
        
        // Adiciona novos eventos
        giftInput.addEventListener('paste', handlePaste);
        giftInput.addEventListener('blur', handleBlur);
        
        console.log('Eventos do gift input configurados');
    }
}

// Funções separadas para os eventos
function handlePaste(e) {
    setTimeout(() => {
        const giftInput = document.getElementById('giftInput');
        const value = giftInput.value.trim();
        console.log('Paste detectado:', value); // Debug
        if (value.length >= 3) {
            handleGiftInput({ target: giftInput });
        }
    }, 100);
}

function handleBlur() {
    const giftInput = document.getElementById('giftInput');
    const value = giftInput.value.trim();
    console.log('Blur detectado:', value); // Debug
    if (value.length >= 3) {
        handleGiftInput({ target: giftInput });
    }
}

document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
