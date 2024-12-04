import sqlite3
import subprocess
import os

def create_db():
    conn = sqlite3.connect('appeals.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS appeals (
            appeal_id INTEGER PRIMARY KEY,
            client_id INTEGER,
            client_name TEXT,
            client_message TEXT,
            manager_comments TEXT,
            closed INTEGER,
            message_id INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS active_users (
            chat_id INTEGER PRIMARY KEY,
            appeal_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

    print("Database and tables created successfully.")

def create_supervisor_config():
    config_content = """
    [supervisord]
    nodaemon=true

    [program:main]
    command=python3 main.py
    directory={project_dir}
    autostart=true
    autorestart=true
    stderr_logfile={project_dir}/supervisor_err.log
    stdout_logfile={project_dir}/supervisor_out.log
    """.format(project_dir=os.path.abspath(os.getcwd()))
    with open('supervisord.conf', 'w') as config_file:
        config_file.write(config_content)

    print("Supervisor config created successfully.")

def start_supervisor():
    subprocess.run(['supervisord', '-c', 'supervisord.conf'])
    print("Supervisor started successfully.")

def run():
    create_db()
    create_supervisor_config()
    start_supervisor()

if __name__ == '__main__':
    run()
