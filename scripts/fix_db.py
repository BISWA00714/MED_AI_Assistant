from app import app
from models import db
from sqlalchemy import text

def fix_db():
    with app.app_context():
        with db.engine.connect() as conn:
            # Check what tables exist
            result = conn.execute(text("SHOW TABLES;"))
            tables = [row[0] for row in result.fetchall()]
            print("Tables:", tables)

            # Check if doctor_requests has online_treatment_fee
            if 'doctor_requests' in tables:
                cols_result = conn.execute(text("SHOW COLUMNS FROM doctor_requests;"))
                cols = [row[0] for row in cols_result.fetchall()]
                print("doctor_requests columns:", cols)
                if 'online_treatment_fee' not in cols:
                    print("Adding online_treatment_fee...")
                    conn.execute(text("ALTER TABLE doctor_requests ADD COLUMN online_treatment_fee INT DEFAULT 0;"))
                    conn.commit()
            
            # Transfer any data from doctor_verification_requests to doctor_requests if it exists
            if 'doctor_verification_requests' in tables and 'doctor_requests' in tables:
                print("Moving data...")
                conn.execute(text("""
                    INSERT INTO doctor_requests (name, specialization, email, phone, education, experience_years, online_treatment_fee, status, created_at)
                    SELECT name, specialization, email, phone, education, experience_years, online_treatment_fee, status, created_at
                    FROM doctor_verification_requests
                """))
                conn.execute(text("DROP TABLE doctor_verification_requests;"))
                conn.commit()

            print("DB Fix Complete.")

if __name__ == '__main__':
    fix_db()
