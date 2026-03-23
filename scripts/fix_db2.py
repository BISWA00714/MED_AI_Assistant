from app import app
from models import db
from sqlalchemy import text

def add_password_col():
    with app.app_context():
        with db.engine.connect() as conn:
            # Check columns
            cols_result = conn.execute(text("SHOW COLUMNS FROM doctor_requests;"))
            cols = [row[0] for row in cols_result.fetchall()]
            if 'password_hash' not in cols:
                print("Adding password_hash to doctor_requests...")
                conn.execute(text("ALTER TABLE doctor_requests ADD COLUMN password_hash VARCHAR(200);"))
                conn.commit()
                print("Added successfully!")
            else:
                print("Column already exists.")

if __name__ == '__main__':
    add_password_col()
