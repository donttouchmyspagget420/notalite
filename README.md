# NotaLite

> Sitio web simple para hacer notas al estilo Notion / Obsidian.

**Primera Entrega del Proyecto**

## Objetivo

NotaLite es una aplicación web de notas con Markdown, carpetas, etiquetas, y notas enlazadas entre sí (wiki-links), pensada para ser simple, rápida y sin fricción.

## Estructura del proyecto

```
NotaLite/
├── app.py                  //punto de entrada, crea y lanza la app
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
    └── llm/
        └── __init__.py     //integracion con modelos de lenguaje (pendiente)
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

### Copia dotenv ejemplo y modifica

`cp .env.example .env`

### Prepara base de datos(solo sqlite)

`flask --app app db init`

`flask --app app db seed`

### Lanza la app

`python app.py`

## Herramientos

`flask --app app db init //crear la base de datos`

`flask --app app db seed //llenarlo`

`flask --app app db clear //limpiarlo`

`flask --app app db check //ver todos las tablas`
