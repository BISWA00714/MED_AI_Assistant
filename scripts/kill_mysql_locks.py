from app import app
from models import db
from sqlalchemy import text

def kill_hanging_queries():
    with app.app_context():
        with db.engine.connect() as conn:
            # Get all processes
            result = conn.execute(text("SHOW PROCESSLIST;"))
            processes = result.fetchall()
            
            for row in processes:
                # row is usually (Id, User, Host, db, Command, Time, State, Info)
                # print(f"Process {row[0]}: {row[4]} - Time: {row[5]} - State: {row[6]} - Info: {row[7]}")
                # Kill queries that are stuck for too long (e.g., hanging ALTER TABLE)
                if row[4] == 'Query' and row[5] > 5:
                    print(f"Killing hanging query ID {row[0]}, Info: {row[7]}")
                    try:
                        conn.execute(text(f"KILL {row[0]};"))
                    except Exception as e:
                        print(f"Error killing {row[0]}: {e}")

if __name__ == "__main__":
    kill_hanging_queries()
    print("Database lock check complete.")
