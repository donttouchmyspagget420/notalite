# NotaLite

> Sitio web simple para hacer notas al estilo Notion / Obsidian.

**Primera Entrega del Proyecto**

## Objetivo

NotaLite es una aplicación web de notas con Markdown, carpetas, etiquetas, y notas enlazadas entre sí (wiki-links), pensada para ser simple, rápida y sin fricción.

## Estructura del proyecto

```
NotaLite/
├── .flaskenv                //FLASK_APP=src para usar la CLI sin --app
├── config.py               //configuracion leida del .env
├── requirements.txt
├── instance/               //base de datos sqlite local
├── static/                 //css, js e imagenes
├── templates/              //vistas Jinja2
└── src/
    ├── __init__.py         //fabrica create_app() y registro de blueprints
    ├── extensions.py       //db, bcrypt, csrf, login_manager, mail
    ├── models.py           //modelos de SQLAlchemy
    ├── cli.py              //comandos flask db
    ├── seed.py             //datos de prueba
    ├── main/
    │   ├── __init__.py     //blueprint main
    │   └── routes.py       //ruta /
    ├── auth/
    │   ├── __init__.py     //blueprint auth
    │   └── routes.py       //login, signup y verificacion
    ├── services/
    │   └── mailer.py       //envio de correos
        └── gemini.py       //asistente de IA para el editor
    ├── settings/
    │   └── routes.py       //perfil, contraseña y tema
```

## Intalacion

### Entorno virtual 

#### linux/macos

`$ mkdir myproject`

`$ cd myproject`

`$ python3 -m venv .venv`

`$ source .venv/bin/activate #depiende de shell(bash,fish,zsh)`

#### windows

`> mkdir myproject`

`> cd myproject`

`> py -3 -m venv .venv`

`> .venv\Scripts\activate`

### Instalar las dependencias

`pip install -r requirements.txt`

### Copia dotenv y flaskenv ejemplo y modifica

`cp .env.example .env`
`cp .flaskenv.example .flaskenv`

### Prepara base de datos(solo sqlite)

`flask db init`

`flask db seed`

### Lanza la app

`flask run`

Flask detecta la app automaticamente gracias al archivo `.flaskenv`.
Si no querés usar `.flaskenv`, el equivalente explicito es:

`flask --app src run`

## Asistente de IA

El editor incluye acciones de IA (resumir, mejorar, continuar, traducir e instrucción personalizada).
Configurá una clave de Google Gemini en `.env`:

`GOOGLE_LLM_API_KEY=tu-clave`

`GOOGLE_LLM_MODEL=gemini-2.0-flash`

## Tests

`python -m unittest discover -s tests -v`

## Herramientas

`flask db init //crear la base de datos`

`flask db seed //llenarlo`

`flask db clear //limpiarlo`

`flask db check //ver todos las tablas`
