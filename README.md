# NotaLite

> Sitio web simple para hacer notas al estilo Notion / Obsidian.

**Primera Entrega del Proyecto**

## Objetivo

NotaLite es una aplicación web de notas con Markdown, carpetas, etiquetas, y notas enlazadas entre sí (wiki-links), pensada para ser simple, rápida y sin fricción.

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

`python migrate.py init`
`python migrate.py seed`

### Lanza la app

`python app.py`

## Herramientos

`python migrate.py init //crear la base de datos`
`python migrate.py seed //llenarlo`
`python migrate.py clear //limpiarlo`
`python migrate.py check //ver todos las tablas`
