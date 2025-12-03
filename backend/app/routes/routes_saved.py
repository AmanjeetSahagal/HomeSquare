import os
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, request

saved = Blueprint("saved", __name__)

# SQLite configuration for saved listings
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # up from app/routes to project root
    "database",
    "homesquare.db",
)


def get_db_connection():
    """Open a new SQLite connection with row dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_saved_listings_table():
    """Create the saved_listings table if it does not exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            address TEXT NOT NULL,
            price REAL,
            estimated_price REAL,
            confidence REAL,
            label TEXT NOT NULL,
            saved_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


@saved.route("/saved_listings", methods=["GET"])
def get_saved_listings():
    """Return all saved listings ordered by most recently saved."""
    conn = get_db_connection()
    cur = conn.execute(
        "SELECT id, url, address, price, estimated_price, confidence, label, saved_at "
        "FROM saved_listings ORDER BY datetime(saved_at) DESC"
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(rows), 200


def _to_float(value):
    """Best-effort conversion to float; returns None on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@saved.route("/saved_listings", methods=["POST"])
def save_listing():
    """Persist a new analyzed listing to SQLite."""
    data = request.get_json(silent=True) or {}

    # Only these fields are strictly required
    required = ["url", "address", "label"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    price = _to_float(data.get("price"))
    est = _to_float(data.get("estimated_price"))
    conf = _to_float(data.get("confidence"))
    if conf is None:
        conf = 0.0

    label = str(data.get("label", "fair")).lower()

    saved_at = datetime.utcnow().isoformat()

    conn = get_db_connection()
    cur = conn.execute(
        """
        INSERT INTO saved_listings (url, address, price, estimated_price, confidence, label, saved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["url"],
            data["address"],
            price,
            est,
            conf,
            label,
            saved_at,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    created = {
        "id": new_id,
        "url": data["url"],
        "address": data["address"],
        "price": price,
        "estimated_price": est,
        "confidence": conf,
        "label": label,
        "saved_at": saved_at,
    }
    return jsonify(created), 201


@saved.route("/saved_listings/<int:item_id>", methods=["DELETE"])
def delete_saved_listing(item_id: int):
    """Delete a saved listing by id."""
    conn = get_db_connection()
    cur = conn.execute("DELETE FROM saved_listings WHERE id = ?", (item_id,))
    conn.commit()
    changes = conn.total_changes
    conn.close()

    if changes == 0:
        return jsonify({"error": "Listing not found."}), 404

    return jsonify({"ok": True}), 200
