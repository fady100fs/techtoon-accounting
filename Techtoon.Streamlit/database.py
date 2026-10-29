import psycopg2
import bcrypt
from contextlib import contextmanager

# نفس قاعدة بيانات Neon المستخدمة في تطبيق C#
CONN_STRING = "host=ep-bitter-night-za726w59-pooler.c-2.eu-west-2.aws.neon.tech port=5432 dbname=neondb user=neondb_owner password=npg_K9nHVkY5OjRC sslmode=require"

@contextmanager
def get_connection():
    conn = psycopg2.connect(CONN_STRING)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_query(query, params=None, fetch=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if fetch:
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return columns, rows
    return None, None

def verify_password(plain_password, hashed_password):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except:
        return False

def hash_password(password):
<<<<<<< HEAD
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
=======
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
