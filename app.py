from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from flask_cors import CORS
import json
import os
import uuid
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.secret_key = 'secret-key'

USERS_FILE = 'users.json'
AGENDAMENTOS_FILE = 'agendamentos.json'
JOINHA_FILE = 'joinha.json'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Dados da Óptica Felíssia
OPTICA_WHATSAPP = '5598970089742'
OPTICA_EMAIL = 'opticafelissia@gmail.com'

# Configuração de e-mail (SMTP)
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'opticafelissia@gmail.com'
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

# Criar pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def carregar_dados(arquivo):
    if not os.path.exists(arquivo):
        with open(arquivo, 'w') as f:
            json.dump([], f)
    with open(arquivo, 'r') as f:
        return json.load(f)

def salvar_dados(arquivo, dados):
    with open(arquivo, 'w') as f:
        json.dump(dados, f, indent=4)

def enviar_email_assunto(nome, cpf, data, horario, endereco, numero, telefone):
    """Envia e-mail para a óptica informando sobre a nova consulta."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = OPTICA_EMAIL
        msg['Subject'] = 'Nova Consulta Agendada'
        
        corpo = f"""
        Olá Óptica Felíssia!
        
        Uma nova consulta foi agendada através do sistema AGENDADOU:
        
        Cliente: {nome}
        CPF: {cpf}
        Data: {data}
        Horário: {horario}
        Endereço: {endereco}, Nº {numero}
        Telefone: {telefone}
        
        Mensagem automática: "Uma consulta realizada"
        
        Aguardando confirmação: "Consulta Confirmada"
        
        ---
        Sistema AGENDADOU - JODEX Soluções em Tecnologias
        """
        
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        
        if SMTP_PASSWORD:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True
        else:
            # Salvar em arquivo caso SMTP não esteja configurado
            print(f"[EMAIL] Mensagem salva (SMTP não configurado): {corpo}")
            return False
    except Exception as e:
        print(f"[EMAIL] Erro ao enviar e-mail: {e}")
        return False

def enviar_whatsapp_oticia(nome, cpf, data, horario, endereco, numero, telefone):
    """Envia mensagem automática para o WhatsApp da óptica."""
    try:
        mensagem = (
            f"Olá Óptica Felíssia!%0A%0A"
            f"Uma consulta realizada:%0A%0A"
            f"*Cliente:* {nome}%0A"
            f"*CPF:* {cpf}%0A"
            f"*Data:* {data}%0A"
            f"*Horário:* {horario}%0A"
            f"*Endereço:* {endereco}, Nº {numero}%0A"
            f"*Telefone:* {telefone}%0A%0A"
            f"Mensagem do sistema: Consulta Confirmada ✅"
        )
        
        # Abrir link do WhatsApp com a mensagem preenchida
        whatsapp_url = f"https://wa.me/{OPTICA_WHATSAPP}?text={mensagem}"
        return whatsapp_url
    except Exception as e:
        print(f"[WHATSAPP] Erro: {e}")
        return None

def enviar_resposta_automatica_cliente(telefone_cliente):
    """
    Simula o envio de resposta automática 'Consulta Confirmada' para o cliente.
    Na prática, isso requer uma API como Twilio ou WhatsApp Business API.
    Aqui retornamos a mensagem que seria enviada.
    """
    mensagem_resposta = "Olá! Sua consulta foi confirmada. ✅\nConsulta Confirmada.\nAguardamos você! - Óptica Felíssia"
    return mensagem_resposta

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    empresa_logo = session.get('empresa_logo', None)
    
    # Carregar estatísticas de joinha
    joinha_data = carregar_dados(JOINHA_FILE)
    positivos = sum(1 for j in joinha_data if j.get('tipo') == 'positivo')
    negativos = sum(1 for j in joinha_data if j.get('tipo') == 'negativo')
    
    return render_template('home.html', 
                          empresa_logo=empresa_logo,
                          joinha_positivos=positivos,
                          joinha_negativos=negativos)

@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    if 'logo' not in request.files:
        return redirect(url_for('home'))
    
    file = request.files['logo']
    
    if file.filename == '':
        return redirect(url_for('home'))
    
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{session['usuario']}_{uuid.uuid4().hex[:8]}.{ext}"
        
        old_logo = session.get('empresa_logo', None)
        if old_logo and os.path.exists(os.path.join(UPLOAD_FOLDER, old_logo)):
            os.remove(os.path.join(UPLOAD_FOLDER, old_logo))
        
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        session['empresa_logo'] = filename
        
        return redirect(url_for('home'))
    
    return redirect(url_for('home'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuarios = carregar_dados(USERS_FILE)
        for usuario in usuarios:
            if usuario['email'] == email and usuario['senha'] == senha:
                session['usuario'] = email
                if 'empresa_logo' in usuario:
                    session['empresa_logo'] = usuario['empresa_logo']
                return redirect(url_for('home'))
        return render_template('login.html', erro="Credenciais inválidas.")
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuarios = carregar_dados(USERS_FILE)
        for usuario in usuarios:
            if usuario['email'] == email:
                return render_template('cadastro.html', erro="Email já cadastrado.")
        usuarios.append({'email': email, 'senha': senha})
        salvar_dados(USERS_FILE, usuarios)
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/agendar', methods=['GET', 'POST'])
def agendar():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    empresa_logo = session.get('empresa_logo', None)
    horarios_disponiveis = ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]
    
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        endereco = request.form['endereco']
        numero = request.form['numero']
        referencia = request.form.get('referencia', '')
        telefone = request.form['telefone']
        data = request.form['data']
        horario = request.form['horario']
        
        agendamentos = carregar_dados(AGENDAMENTOS_FILE)
        
        novo_agendamento = {
            'usuario': session['usuario'], 
            'nome': nome,
            'cpf': cpf,
            'endereco': endereco,
            'numero': numero,
            'referencia': referencia,
            'telefone': telefone,
            'data': data,
            'horario': horario,
            'status': 'agendado',
            'data_criacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        agendamentos.append(novo_agendamento)
        salvar_dados(AGENDAMENTOS_FILE, agendamentos)
        
        # Enviar e-mail para a óptica
        enviar_email_assunto(nome, cpf, data, horario, endereco, numero, telefone)
        
        # Gerar link WhatsApp para a óptica
        whatsapp_oticia_url = enviar_whatsapp_oticia(nome, cpf, data, horario, endereco, numero, telefone)
        
        # Gerar resposta automática para o cliente
        resposta_cliente = enviar_resposta_automatica_cliente(telefone)
        
        # Mensagem de sucesso personalizada
        mensagem_sucesso = f"Olá {nome}! Seu agendamento para o dia {data} às {horario} foi realizado com sucesso."
        
        # Gerar link do WhatsApp do cliente para confirmação
        texto_cliente = (
            f"Olá Óptica Felíssia! Gostaria de confirmar meu agendamento de consulta de vista.%0A%0A"
            f"*Nome:* {nome}%0A"
            f"*CPF:* {cpf}%0A"
            f"*Data:* {data}%0A"
            f"*Horário:* {horario}%0A"
            f"*Endereço:* {endereco}, Nº {numero}%0A"
            f"*Referência:* {referencia}%0A"
            f"*Telefone:* {telefone}"
        )
        whatsapp_cliente_url = f"https://wa.me/{OPTICA_WHATSAPP}?text={texto_cliente}"
        
        return render_template('agendar.html', 
                               mensagem=mensagem_sucesso, 
                               resposta_ia=resposta_cliente,
                               agendamento=novo_agendamento, 
                               horarios=horarios_disponiveis,
                               whatsapp_cliente_url=whatsapp_cliente_url,
                               whatsapp_oticia_url=whatsapp_oticia_url)
    
    return render_template('agendar.html', horarios=horarios_disponiveis, empresa_logo=empresa_logo)

@app.route('/catalogo')
def catalogo():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    empresa_logo = session.get('empresa_logo', None)
    return render_template('catalogo.html', empresa_logo=empresa_logo)

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        whatsapp = request.form['whatsapp']
        return render_template('recuperar_senha.html', mensagem="Se um código for encontrado, ele será enviado para o seu WhatsApp.")
    return render_template('recuperar_senha.html')

@app.route('/agendamentos')
def agendamentos():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    agendamentos = carregar_dados(AGENDAMENTOS_FILE)
    user_agendamentos = [a for a in agendamentos if a['usuario'] == session['usuario']]
    empresa_logo = session.get('empresa_logo', None)
    return render_template('agendamentos.html', agendamentos=user_agendamentos, empresa_logo=empresa_logo)

# ========== SISTEMA DE JOINHA (AVALIAÇÃO) ==========

@app.route('/joinha', methods=['POST'])
def registrar_joinha():
    if 'usuario' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    tipo = request.json.get('tipo')  # 'positivo' ou 'negativo'
    
    if tipo not in ['positivo', 'negativo']:
        return jsonify({'erro': 'Tipo inválido'}), 400
    
    joinha_data = carregar_dados(JOINHA_FILE)
    
    # Verificar se o usuário já votou hoje
    hoje = datetime.now().strftime('%Y-%m-%d')
    ja_votou = False
    for j in joinha_data:
        if j.get('usuario') == session['usuario'] and j.get('data', '').startswith(hoje):
            # Atualizar voto
            j['tipo'] = tipo
            j['data'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ja_votou = True
            break
    
    if not ja_votou:
        joinha_data.append({
            'usuario': session['usuario'],
            'tipo': tipo,
            'data': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    salvar_dados(JOINHA_FILE, joinha_data)
    
    positivos = sum(1 for j in joinha_data if j.get('tipo') == 'positivo')
    negativos = sum(1 for j in joinha_data if j.get('tipo') == 'negativo')
    
    return jsonify({
        'sucesso': True,
        'positivos': positivos,
        'negativos': negativos
    })

@app.route('/joinha_stats')
def joinha_stats():
    if 'usuario' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    joinha_data = carregar_dados(JOINHA_FILE)
    
    # Verificar se já votou hoje
    hoje = datetime.now().strftime('%Y-%m-%d')
    voto_hoje = None
    for j in joinha_data:
        if j.get('usuario') == session['usuario'] and j.get('data', '').startswith(hoje):
            voto_hoje = j.get('tipo')
            break
    
    positivos = sum(1 for j in joinha_data if j.get('tipo') == 'positivo')
    negativos = sum(1 for j in joinha_data if j.get('tipo') == 'negativo')
    
    return jsonify({
        'positivos': positivos,
        'negativos': negativos,
        'total': len(joinha_data),
        'voto_hoje': voto_hoje
    })

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('empresa_logo', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
