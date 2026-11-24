# Pinboard — Pinterest style project

A small full-stack inspiration board built with HTML, CSS, JavaScript, Flask, SQLite, and JWT. It includes a searchable catalog of 120 curated inspiration images across home decor, fashion, food, travel, art, and beauty, alongside user uploads. Users can register/login, search pins, upload image pins, and save/unsave their own pins. Gallery images are hosted by Unsplash and need an internet connection; user-uploaded images are stored by the app.

## Run locally (Windows PowerShell)

```powershell
cd pinterest-clone
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:JWT_SECRET_KEY = "replace-this-with-a-long-random-local-secret"
python app.py
```

Open http://127.0.0.1:5000. The database (`pinterest.db`) is created on first run. The first account can be created using **Sign up**. Search matches gallery and uploaded pin titles/descriptions. Uploads accept PNG/JPG/GIF/WEBP up to 8 MB. Gallery pins are inspiration examples; use **Create a pin** to upload and save your own image to the local database.

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again. To stop the server press Ctrl+C; to leave the virtual environment type `deactivate`.

## Render deployment

Push this folder to a GitHub repository, then in Render choose **New → Blueprint** and connect the repository. Select `pinterest-clone/render.yaml` if Render asks for the blueprint path. It configures Gunicorn, generates a JWT secret, and mounts a persistent disk for the SQLite database and uploaded images. The paid persistent disk keeps user data across deploys; free instances do not provide durable local disk storage. After deploy, open the service URL.

You can also create a Render Web Service with root directory `pinterest-clone`, build command `pip install -r requirements.txt`, start command `gunicorn app:app`, and environment variables `JWT_SECRET_KEY` (a long random secret), `DATABASE_PATH=/var/data/pinterest.db`, `UPLOAD_FOLDER=/var/data/uploads`, plus a persistent disk mounted at `/var/data`.

## Security and scope

Passwords are hashed. JWT secrets use an environment variable; the fallback exists for local development only. Set a unique secret in production. This is an instructor project starter, without moderation, image CDN, password reset, or production account recovery.
