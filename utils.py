from sqlite3 import IntegrityError


def get_user_or_none(user_id, cursor):
    row = cursor.execute(f"SELECT * FROM users WHERE user_id = {user_id}")
    data = row.fetchone()
    if not data:
        return None
    return data


def create_user(user_id, chat_id, cursor, conn):
    try:
        cursor.execute(f"INSERT INTO users (user_id, chat_id, admin_status, notifications_status) VALUES({user_id}, {chat_id}, 0, 1);")
        conn.commit()
    except IntegrityError:
        pass


def start_user_notifications(user_id, cursor, conn):
    cursor.execute(f"UPDATE users SET notifications_status = 1 WHERE user_id = {user_id};")
    conn.commit()


def stop_user_notifications(user_id, cursor, conn):
    cursor.execute(f"UPDATE users SET notifications_status = 0 WHERE user_id = {user_id};")
    conn.commit()

def set_admin_status(user_id, cursor, conn):
    cursor.execute(f"UPDATE users SET admin_status = 1 WHERE user_id = {user_id};")
    conn.commit()

def get_all_users(cursor):
    rows = cursor.execute(f"SELECT * FROM users")
    data = rows.fetchall()
    return data

def get_bot_stats(cursor):
    rows = cursor.execute(f"SELECT * FROM users")
    data = rows.fetchall()
    users_amount = len(data)
    active_users = 0

    for i in data:
        if i['notifications_status']: active_users += 1

    return f"Бот запустили __{users_amount}__ чел\., из них включили уведомления: __{active_users}__\."
