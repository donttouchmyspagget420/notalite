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
├── docs/                   //documentacion y mockups
├── instance/               //base de datos sqlite local
├── static/                 //css, js e imagenes
├── templates/              //vistas Jinja2
└── src/
    ├── __init__.py         //fabrica create_app() y registro de blueprints
    ├── extensions.py       //db, bcrypt, csrf, login_manager, mail
    ├── models.py           //modelos de SQLAlchemy y reglas de cascada
    ├── cli.py              //comandos flask db y flask tests
    ├── seed.py             //datos de prueba
    ├── auth/
    │   ├── __init__.py     //blueprint auth
    │   └── routes.py       //login, signup y verificacion
    ├── enums/
    │   └── *.py            //limites y constantes de la aplicacion
    ├── main/
    │   ├── __init__.py     //blueprint main
    │   └── routes.py       //ruta /
    ├── notes/
    │   ├── __init__.py     //blueprint notes
    │   ├── routes.py       //notas, carpetas, etiquetas, buscador y papelera
    │   ├── utils.py        //helpers de acceso, busqueda y barra lateral
    │   └── exporters.py    //exportacion a Markdown y PDF
    ├── admin/
    │   ├── __init__.py     //blueprint admin
    │   └── routes.py       //usuarios y metricas (solo administradores)
    ├── services/
    │   ├── forms.py        //formularios y validacion WTForms
    │   ├── gemini.py       //asistente de IA para el editor
    │   ├── google.py       //OAuth con Google
    │   ├── mailer.py       //envio de correos
    │   └── storage.py      //imagenes en disco local o S3
    ├── settings/
    │   ├── __init__.py     //blueprint settings
    │   └── routes.py       //perfil, contraseña, tema e import/export
    └── tests/
        ├── base.py         //configuracion base de los tests
        ├── test_models.py  //cascadas y relaciones
        └── test_*.py       //tests de la aplicacion
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

## Imágenes en notas

Desde el editor podés insertar imágenes con el botón «Imagen». Se guardan en
`UPLOAD_FOLDER` (por defecto `storage/`) y se insertan en el Markdown como
`![descripción](url)`.

Para guardarlas en Amazon S3 (o un servicio compatible con S3) configurá en
`.env`:

`STORAGE_BACKEND=s3`

`AWS_REGION=us-east-1`

`AWS_S3_BUCKET=tu-bucket`

`AWS_ACCESS_KEY_ID=...`

`AWS_SECRET_ACCESS_KEY=...`

Opcionalmente podés definir `AWS_S3_PREFIX`, `AWS_S3_PUBLIC_URL`,
`AWS_S3_ENDPOINT_URL` y `AWS_S3_ACL`.

## Compartir notas

El botón «Compartir» del editor permite buscar una cuenta por nombre o email,
elegir el permiso (solo lectura o edición) y administrar quién tiene acceso.
Las notas compartidas aparecen en «Compartidas» dentro de la barra lateral.

## Buscar notas

El buscador de la barra lateral (o `Ctrl/Cmd + K`) recorre títulos, contenido y
etiquetas. Permite filtrar por campo y muestra un fragmento resaltado de cada
resultado. También incluye las notas que otras personas compartieron con vos.

## Papelera

Al eliminar una nota se mueve a la papelera, donde se puede restaurar o borrar
definitivamente. Las notas se eliminan solas a los 30 días. La papelera muestra
cuántos días le quedan a cada nota y permite vaciarla por completo.

## Administración

Las cuentas con rol `Admin` ven la sección «Usuarios y métricas» en la barra
lateral. Allí pueden consultar usuarios, actividad semanal, espacio utilizado y
las cuentas creadas recientemente. El panel es de solo lectura.

## Miniaturas en las listas

Si una nota contiene una imagen en su Markdown o HTML, la primera imagen se usa
como miniatura en las listas de Inicio, Carpetas, Etiquetas, Compartidas,
Buscador y Papelera. Si no tiene imágenes se muestra la inicial del título.

## Tests

`flask tests run`

También se puede ejecutar un módulo, clase o test concreto:

`flask tests run src.tests.test_notes`

`flask tests run src.tests.test_notes.NotesTestCase.test_export_pdf`

O usar `unittest` directamente:

`python -m unittest discover -s src/tests -v`

## Herramientas

`flask tests run //ejecutar los tests`

`flask db init //crear la base de datos`

`flask db seed //llenarlo`

`flask db clear //limpiarlo`

`flask db check //ver todos las tablas`
