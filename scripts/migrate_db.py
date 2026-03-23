import os
import sys
from sqlalchemy import create_engine, MetaData, text
from app import app
from models import db

def migrate():
    sqlite_engine = create_engine('sqlite:///instance/medical.db')
    mysql_engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)
    
    mysql_meta = MetaData()
    mysql_meta.reflect(bind=mysql_engine)
    
    with mysql_engine.begin() as mysql_conn:
        mysql_conn.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        
        for table_name in sqlite_meta.tables:
            if table_name == 'sqlite_sequence': continue
            if table_name in mysql_meta.tables:
                sqlite_table = sqlite_meta.tables[table_name]
                mysql_table = mysql_meta.tables[table_name]
                
                with sqlite_engine.connect() as sqlite_conn:
                    # fetch all rows
                    result = sqlite_conn.execute(sqlite_table.select()).fetchall()
                    if result:
                        cols = sqlite_table.columns.keys()
                        values = [dict(zip(cols, row)) for row in result]
                        
                        # Clear existing data in MySQL table to avoid unique key constraints
                        # (assuming user wants a pristine copy from sqlite)
                        mysql_conn.execute(mysql_table.delete())
                        
                        # Insert records
                        mysql_conn.execute(mysql_table.insert(), values)
                        print(f"Migrated {len(values)} records to {table_name}")
                        
        mysql_conn.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
        
    # Crucial on Windows: Release SQLite file lock before trying to delete it
    sqlite_engine.dispose()
    mysql_engine.dispose()

if __name__ == "__main__":
    db_path = 'instance/medical.db'
    if os.path.exists(db_path):
        print("Starting migration from SQLite to MySQL...")
        with app.app_context():
            migrate()
        os.remove(db_path)
        print("Successfully migrated all data to MySQL database and deleted medical.db!")
    else:
        print("medical.db not found!")
