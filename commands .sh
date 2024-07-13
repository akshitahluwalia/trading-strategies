# Command Template

cd developer/trading-strategies/ && \
source env/bin/activate && \
python accumulator_v2.py \
--token="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2NjkyM2U5ZWNiODFjYzFmODJjNGZlZmIiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIwODYwMzE4LCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjA5MDgwMDB9.yTNnmqKgqJdx-ZmTk_zr30YhSiwBGwqradi1lRhI6lk" \
--lots="2" \
--option="CE" \
--underlying="NSE_INDEX|Nifty Bank" \
--instrumentmasterpath="instruments.csv" \
--expiry="2024-07-16"