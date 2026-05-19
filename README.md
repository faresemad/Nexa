# Nexa
nexa media

# Clone and setup

git clone <repo-url>
cd nexa-social-recovery

# Copy env file and update with your credentials

cp .env.example .env

# Start services

docker-compose up -d

# Run migrations

docker-compose exec app python manage.py migrate

# Seed demo data

docker-compose exec app python manage.py seed_data

# Access API docs

open <http://localhost:8000/api/docs/>
