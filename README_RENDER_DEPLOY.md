# Deploy no Render (Django)

## 1) Subir para o GitHub
- Crie um repositório no GitHub
- Faça commit do projeto inteiro

## 2) Criar Postgres no Render
- Dashboard Render -> New -> PostgreSQL
- Copie a variável `DATABASE_URL`

## 3) Criar Web Service
- New -> Web Service -> conectar no repo
- **Build Command:** `./build.sh`
- **Start Command:** `gunicorn backend.wsgi:application`

## 4) Variáveis de ambiente (Web Service -> Environment)
Crie estas variáveis:

- `SECRET_KEY` = uma chave forte
- `DEBUG` = `False`
- `ALLOWED_HOSTS` = `seuapp.onrender.com`
- `CSRF_TRUSTED_ORIGINS` = `https://seuapp.onrender.com`
- `DATABASE_URL` = (colar a do Postgres do Render)

Se usar Mercado Pago:
- `MERCADOPAGO_ACCESS_TOKEN` = seu token
- `SITE_BASE_URL` = `https://seuapp.onrender.com`
- `MERCADOPAGO_WEBHOOK_SECRET` = um segredo seu

## 5) Primeira vez (admin)
Após o deploy, crie um super usuário pelo Shell do Render:

```bash
python manage.py createsuperuser
```
