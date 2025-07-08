from enum import Enum
from collections import defaultdict
from operator import getitem


class SentimentTypeEnum(str, Enum):
    neutral = "neutral"
    negative = "negative"
    positive = "positive"

    @classmethod
    def fields(cls):
        return [member for member in cls.__members__]  # type: ignore


class SentimentAnalysis:
    _data: dict[str, str] = {
        "хорош": SentimentTypeEnum.positive,
        "люблю": SentimentTypeEnum.positive,
        "плохо": SentimentTypeEnum.negative,
        "ненавиж": SentimentTypeEnum.negative,
    }

    def analyze(self, text: str):
        sentiment_score: dict[str, int] = defaultdict(int)

        for word in text.strip().split():
            # XXX: Case-insensitive
            word = word.lower()

            for key, value in self._data.items():
                if key not in word:
                    continue
                sentiment_score[value] += 1

        result: list[str] = sorted(
            sentiment_score,
            key=lambda item: getitem(item, 1),
        )
        if not result:
            result.append(SentimentTypeEnum.neutral)

        # NOTE: No comparison
        # positive=2, negative=2 -> positive | negative
        return result[0].value  # type: ignore  :)
