# Fitness Tracker — FastAPI Backend

## Project structure

```
fitness_app/
├── main.py              # App entry point, routers registered here
├── database.py          # asyncpg connection pool + table creation
├── requirements.txt
├── models/
│   └── schemas.py       # Pydantic request/response models
└── routers/
    ├── meals.py         # GET/POST/PATCH/DELETE /meals
    ├── weight.py        # GET/POST/PATCH/DELETE /weight
    └── workouts.py      # GET/POST/PATCH/DELETE /workouts + /sets
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the PostgreSQL database

```sql
CREATE DATABASE fitness;
```

Then run the `fitness_schema.sql` file if you want the views pre-created,
or just start the app — it creates the tables automatically on startup.

### 4. Set your database URL

Either export it as an environment variable:

```bash
export DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/fitness"
```

Or edit the default value in `database.py` directly.

### 5. Run the app

```bash
uvicorn main:app --reload
```

The API is now running at **http://localhost:8000**

## Interactive docs

FastAPI generates interactive docs automatically:

- **Swagger UI** → http://localhost:8000/docs
- **ReDoc**       → http://localhost:8000/redoc

You can test every endpoint directly in the browser — no extra tools needed.

## API overview

| Method | Endpoint                          | Description                  |
|--------|-----------------------------------|------------------------------|
| POST   | /meals                            | Log a meal                   |
| GET    | /meals                            | List meals (filterable)       |
| GET    | /meals/summary                    | Daily nutrition totals        |
| GET    | /meals/{id}                       | Get one meal                  |
| PATCH  | /meals/{id}                       | Update a meal                 |
| DELETE | /meals/{id}                       | Delete a meal                 |
| POST   | /weight                           | Log a weight entry            |
| GET    | /weight                           | List entries + 7-day avg      |
| GET    | /weight/{id}                      | Get one entry                 |
| PATCH  | /weight/{id}                      | Update an entry               |
| DELETE | /weight/{id}                      | Delete an entry               |
| POST   | /workouts                         | Log a workout (with sets)     |
| GET    | /workouts                         | List workouts                 |
| GET    | /workouts/{id}                    | Get one workout + its sets    |
| PATCH  | /workouts/{id}                    | Update workout details        |
| DELETE | /workouts/{id}                    | Delete workout + sets         |
| POST   | /workouts/{id}/sets               | Add a set to a workout        |
| DELETE | /workouts/{id}/sets/{set_id}      | Delete a set                  |

## Connecting the Streamlit dashboard

Point `dashboard.py` at the same database and run both together:

```bash
# Terminal 1
uvicorn main:app --reload

# Terminal 2
streamlit run dashboard.py
```
