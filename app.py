import sqlite3
import datetime
from enum import Enum
from typing import Any
from operator import getitem
from collections import defaultdict

from flask import Flask
from flask import Blueprint
from flask import Response
from flask import request
from flask import redirect
from flask import url_for
from flask import abort
from flask import g


class SentimentTypeEnum(Enum):
    neutral = "neutral"
    negative = "negative"
    positive = "positive"


SENTIMENT_DATA: dict[str, SentimentTypeEnum] = {
    "хорош": SentimentTypeEnum.positive,
    "люблю": SentimentTypeEnum.positive,
    "плохо": SentimentTypeEnum.negative,
    "ненавиж": SentimentTypeEnum.negative,
}
MISSING_PAYLOAD_EXCEPTION: Response = Response(
    response='Необходимо передать json: `{ "text": "ваш отзыв" }`',
    status=400,
)
WRONG_SENTIMENT_EXCEPTION: Response = Response(
    response="Неалидный `sentiment`: "
    + " | ".join(
        SentimentTypeEnum.__members__,
    ),
    status=400,
)


def db_connection() -> sqlite3.Connection:
    return sqlite3.connect("reviews.db")


def get_db():
    conn = getattr(g, "_database", None)

    if conn is None:
        conn = db_connection()
        conn.row_factory = sqlite3.Row
        g._database = conn

    return conn


app = Flask(__name__)


@app.errorhandler(404)
def page_not_found(_):
    return redirect(url_for("reviews.index"))


reviews = Blueprint(
    name="reviews",
    import_name="reviews",
    url_prefix="/reviews",
)


@reviews.route("", methods=["GET", "POST"])
def index() -> list[dict] | dict:
    conn: sqlite3.Connection = get_db()
    curr: sqlite3.Cursor = conn.cursor()

    if request.method == "POST":
        if not request.is_json:
            abort(MISSING_PAYLOAD_EXCEPTION)

        data: dict = request.get_json()
        text: Any | None = data.get("text")
        if text is None:
            abort(MISSING_PAYLOAD_EXCEPTION)

        text = str(text)

        sql = """
        INSERT INTO reviews (
            text, sentiment, created_at
        )
        VALUES (
            ?, ?, ?
        )
        RETURNING *;
        """
        sentiment_score: dict[SentimentTypeEnum, int] = defaultdict(int)
        text_sentiment: SentimentTypeEnum = SentimentTypeEnum.neutral

        for word in text.strip().split():
            # XXX: Case-insensitive
            word = word.lower()

            for key, value in SENTIMENT_DATA.items():
                if key not in word:
                    continue
                sentiment_score[value] += 1

        found_sentiments: list[SentimentTypeEnum] = sorted(
            sentiment_score,
            key=lambda item: getitem(item, 1),  # type: ignore
        )
        if found_sentiments:
            # NOTE: No comparison
            # positive=2, negative=2 -> positive | negative
            text_sentiment = getitem(found_sentiments, 0)

        created_at: str = datetime.datetime.now(
            tz=datetime.timezone.utc,
        ).isoformat()

        curr.execute(sql, (text, text_sentiment.value, created_at))
        result = curr.fetchone()
        conn.commit()

        return dict(result)

    sql: str = "SELECT * FROM reviews"
    parameters: list[str] = []

    sentiment: str | None = request.args.get("sentiment")
    if sentiment:
        # XXX: Case-insensitive
        sentiment = sentiment.lower()

        if sentiment not in SentimentTypeEnum.__members__:
            abort(WRONG_SENTIMENT_EXCEPTION)

        parameters.append(sentiment)
        sql += " WHERE sentiment=?"

    sql += " ORDER BY created_at DESC"

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

    app.register_blueprint(reviews)

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()
