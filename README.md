# Django Webserver

## Install packages

1. Clone repository:
```bash
git clone <repository-url>
cd Django-webserver
```

2. Create and activate venv:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. Install requirements:
```bash
pip install -r requirements.txt
```

4. Establish env var:
```bash
cp .env.example .env
```

5. Generate a secure Django SECRET_KEY:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

6. Change file `.env` with your config:
```bash
# Database settings
DB_ENGINE=django.db.backends.postgresql
DB_NAME=database_name
DB_USER=database_user
DB_PASSWORD=database_password
DB_HOST=localhost
DB_PORT=5432

# Django settings
SECRET_KEY=secret_key

# Cloudinary settings
CLOUDINARY_CLOUD_NAME=cloud_name
CLOUDINARY_API_KEY=api_key
CLOUDINARY_API_SECRET=api_secret

# Device Management settings
DEVICE_MANAGEMENT_PASSWORD=secure_password
```

7. Run migration to set up database:
```bash
python manage.py makemigrations cartv2
python manage.py migrate cartv2
```

8. Run server:
```bash
# Debug mode
python manage.py runserver
# Gunicorn
gunicorn --workers 3 --bind ipaddress:port cartv2.wsgi 
```