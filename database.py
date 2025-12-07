# database.py
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from config import DB_PATH, SERVICES, REFERRAL_BONUS_LEVEL2


# ---------------------------------------
# Bazaga ulanish
# ---------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------
# DB INIT – barcha jadvalar
# ---------------------------------------
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # foydalanuvchilar
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            referrer_id INTEGER,
            created_at TEXT,
            last_active_at TEXT
        )
        """
    )

    # referallar
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            level INTEGER,
            created_at TEXT
        )
        """
    )

    # xizmat so'rovlari
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS service_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_key TEXT,
            cost REAL,
            status TEXT,
            created_at TEXT,
            approved_at TEXT,
            admin_id INTEGER
        )
        """
    )

    # admin /givepoint orqali qo‘shgan qo‘lda ballar
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS manual_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            points REAL,
            comment TEXT,
            admin_id INTEGER,
            created_at TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# ---------------------------------------
# Users
# ---------------------------------------
def add_or_update_user(
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    referrer_id: Optional[int],
) -> bool:
    """
    True qaytaradi agar user yangi bo'lsa, False agar eski bo'lsa.
    """
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            """
            INSERT INTO users (user_id, username, first_name, last_name, referrer_id, created_at, last_active_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, first_name, last_name, referrer_id, now, now),
        )
        conn.commit()
        conn.close()
        if referrer_id:
            register_referral_chain(referrer_id, user_id)
        return True
    else:
        cur.execute(
            """
            UPDATE users SET username = ?, first_name = ?, last_name = ?, last_active_at = ?
            WHERE user_id = ?
            """,
            (username, first_name, last_name, now, user_id),
        )
        conn.commit()
        conn.close()
        return False


def touch_user_activity(user_id: int):
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET last_active_at = ? WHERE user_id = ?",
        (now, user_id),
    )
    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
        (username,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------
# Referrals & points
# ---------------------------------------
def register_referral_chain(referrer_id: int, new_user_id: int):
    """
    1-daraja referal + agar referrerning ham referreri bo‘lsa – 2-daraja referal.
    """
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()

    # Level 1
    cur.execute(
        """
        INSERT INTO referrals (referrer_id, referred_id, level, created_at)
        VALUES (?, ?, 1, ?)
        """,
        (referrer_id, new_user_id, now),
    )

    # Level 2 (referrerning referreri)
    cur.execute(
        "SELECT referrer_id FROM users WHERE user_id = ?",
        (referrer_id,),
    )
    row = cur.fetchone()
    if row and row["referrer_id"]:
        lvl2 = row["referrer_id"]
        cur.execute(
            """
            INSERT INTO referrals (referrer_id, referred_id, level, created_at)
            VALUES (?, ?, 2, ?)
            """,
            (lvl2, new_user_id, now),
        )

    conn.commit()
    conn.close()


def get_referral_stats(user_id: int) -> Dict[str, Any]:
    """
    Referal ballari:
    - Level 1: har biri 1 ball
    - Level 2: REFERRAL_BONUS_LEVEL2 (masalan 0.25) * soni
    + manual_points dan qo‘shilgan ballar
    - service_requests dan ishlatilgan ballar (pending + approved)
    """
    conn = get_connection()
    cur = conn.cursor()

    # Level 1 soni
    cur.execute(
        "SELECT COUNT(*) AS c FROM referrals WHERE referrer_id = ? AND level = 1",
        (user_id,),
    )
    l1 = cur.fetchone()["c"]

    # Level 2 raw soni
    cur.execute(
        "SELECT COUNT(*) AS c FROM referrals WHERE referrer_id = ? AND level = 2",
        (user_id,),
    )
    l2_raw = cur.fetchone()["c"]

    l2_bonus = int(l2_raw * REFERRAL_BONUS_LEVEL2)

    # Qo‘lda qo‘shilgan (manual) ballar
    cur.execute(
        "SELECT COALESCE(SUM(points), 0) AS total FROM manual_points WHERE user_id = ?",
        (user_id,),
    )
    manual_total = cur.fetchone()["total"] or 0

    # Umumiy ball = referal + manual
    total_points = l1 + l2_bonus + int(manual_total)

    # Pending + approved so'rovlarga ketgan balllar
    cur.execute(
        """
        SELECT IFNULL(SUM(cost), 0) AS s
        FROM service_requests
        WHERE user_id = ? AND status IN ('pending', 'approved')
        """,
        (user_id,),
    )
    reserved = cur.fetchone()["s"] or 0

    available_points = max(total_points - reserved, 0)

    conn.close()
    return {
        "level1_count": l1,
        "level2_raw": l2_raw,
        "level2_bonus": l2_bonus,
        "manual_total": int(manual_total),
        "total_points": int(total_points),
        "available_points": int(available_points),
    }


def get_level1_users_with_stats(user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT u.user_id, u.username, COUNT(r2.id) AS level1_count
        FROM referrals r
        JOIN users u ON u.user_id = r.referred_id
        LEFT JOIN referrals r2 ON r2.referrer_id = u.user_id AND r2.level = 1
        WHERE r.referrer_id = ? AND r.level = 1
        GROUP BY u.user_id, u.username
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_active_referral_stats(user_id: int, days: int) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM referrals r
        JOIN users u ON u.user_id = r.referred_id
        WHERE r.referrer_id = ? AND r.level = 1 AND u.last_active_at >= ?
        """,
        (user_id, since),
    )
    l1 = cur.fetchone()["c"]

    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM referrals r
        JOIN users u ON u.user_id = r.referred_id
        WHERE r.referrer_id = ? AND r.level = 2 AND u.last_active_at >= ?
        """,
        (user_id, since),
    )
    l2_raw = cur.fetchone()["c"]

    l2_bonus = int(l2_raw * REFERRAL_BONUS_LEVEL2)
    total_points = l1 + l2_bonus

    conn.close()
    return {
        "level1_count": l1,
        "level2_raw": l2_raw,
        "level2_bonus": l2_bonus,
        "total_points": total_points,
    }


def get_leaderboard(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Leaderboard: hamma userlar bo‘yicha total_points hisoblaymiz.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id, username FROM users")
    users = cur.fetchall()
    conn.close()

    result = []
    for u in users:
        stats = get_referral_stats(u["user_id"])
        result.append(
            {
                "user_id": u["user_id"],
                "username": u["username"],
                "total_points": stats["total_points"],
            }
        )

    result.sort(key=lambda x: x["total_points"], reverse=True)
    return result[:limit]


# ---------------------------------------
# Service requests
# ---------------------------------------
def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM users")
    users = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM service_requests WHERE status = 'pending'")
    pending = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM service_requests WHERE status = 'approved'")
    approved = cur.fetchone()["c"]

    conn.close()
    return {"users": users, "pending": pending, "approved": approved}


def get_pending_requests():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM service_requests
        WHERE status = 'pending'
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_service_request(user_id: int, service_key: str, cost: float) -> int:
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO service_requests (user_id, service_key, cost, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (user_id, service_key, cost, now),
    )
    req_id = cur.lastrowid
    conn.commit()
    conn.close()
    return req_id


def get_user_services(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM service_requests
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def approve_latest_request_for_user(user_id: int, admin_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT * FROM service_requests
        WHERE user_id = ? AND status = 'pending'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        UPDATE service_requests
        SET status = 'approved', approved_at = ?, admin_id = ?
        WHERE id = ?
        """,
        (now, admin_id, row["id"]),
    )
    conn.commit()
    conn.close()
    return dict(row)


# ---------------------------------------
# Manual points ( /givepoint )
# ---------------------------------------
def add_manual_points(user_id: int, points: float, comment: str, admin_id: int):
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO manual_points (user_id, points, comment, admin_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, points, comment, admin_id, now),
    )
    conn.commit()
    conn.close()


def get_manual_points_sum(user_id: int) -> float:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(points), 0) AS total FROM manual_points WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return float(row["total"] or 0)


# ---------------------------------------
# Excel export
# ---------------------------------------
def export_users_to_excel(path: str):
    try:
        import openpyxl
    except ImportError:
        return False

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Users"

    headers = [
        "user_id",
        "username",
        "first_name",
        "last_name",
        "referrer_id",
        "created_at",
        "last_active_at",
    ]
    ws.append(headers)

    for r in rows:
        ws.append([r[h] for h in headers])

    wb.save(path)
    return True
