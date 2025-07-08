import sqlite3
import datetime

from flask import Flask
from flask import Response
from flask import abort
from flask import request
from flask import redirect
from flask import url_for
from flask import g

from src.sentiment_analysis import SentimentTypeEnum
from src.sentiment_analysis import SentimentAnalysis


app = Flask(__name__)


def db_connection() -> sqlite3.Connection:
    return sqlite3.connect("reviews.db")


def get_db():
    conn = getattr(g, "_database", None)

    if conn is None:
        conn = db_connection()
        conn.row_factory = sqlite3.Row
        g._database = conn

    return conn


MISSING_PAYLOAD_EXCEPTION = Response(
    response='Необходимо передать json: `{ "text": "ваш отзыв" }`',
    status=400,
)
WRONG_SENTIMENT_EXCEPTION = Response(
    response="Неалидный `sentiment`: "
    + " | ".join(
        SentimentTypeEnum.__members__,
    ),
    status=400,
)


@app.errorhandler(404)
def page_not_found(_):
    return redirect(url_for("reviews"))


@app.route("/reviews", methods=["GET", "POST"])
def reviews() -> list[dict] | dict:
    conn: sqlite3.Connection = get_db()
    curr: sqlite3.Cursor = conn.cursor()

    if request.method == "POST":
        if not request.is_json:
            abort(MISSING_PAYLOAD_EXCEPTION)

        data: dict = request.get_json()
        text: str | None = data.get("text")
        if text is None:
            abort(MISSING_PAYLOAD_EXCEPTION)

        sql = """
        INSERT INTO reviews (
            text, sentiment, created_at
        )
        VALUES (
            ?, ?, ?
        )
        RETURNING *;
        """
        sentiment = SentimentAnalysis().analyze(text=text)

        created_at = datetime.datetime.now(
            tz=datetime.timezone.utc,
        ).isoformat()

        curr.execute(sql, (text, sentiment, created_at))
        result = curr.fetchone()
        conn.commit()

        return dict(result)

    # XXX: No `order`
    sql: str = "SELECT * FROM reviews"
    parameters: list[str] = []

    sentiment: str | None = request.args.get("sentiment")
    if sentiment:
        # XXX: Case-insensitive
        sentiment = sentiment.lower()

        # XXX: Won't raise any ValidationErrors'
        if sentiment not in SentimentTypeEnum.fields():
            abort(WRONG_SENTIMENT_EXCEPTION)

        parameters.append(sentiment)
        sql += " WHERE sentiment=?"

    curr.execute(sql, parameters)

    return [dict(item) for item in curr.fetchall()]


if __name__ == "__main__":
    conn: sqlite3.Connection = db_connection()
    curr: sqlite3.Cursor = conn.cursor()
    curr.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            text        TEXT NOT NULL,
            sentiment   TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );
        """
    )
    conn.commit()

    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()
