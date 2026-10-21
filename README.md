# Óptica Felíssia - AGENDADOU

Aplicação Flask para agendamentos, botão de confirmação via WhatsApp e painel administrativo.

## Execução no Render

Build Command: `pip install -r requirements.txt`
Start Command: `gunicorn app:app`

## Variáveis administrativas

Configure no Render: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SECRET_KEY` e, opcionalmente, `SMTP_PASSWORD`.

Painel: `/admin`
