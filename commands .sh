eval "$(ssh-agent -s)" && ssh-add ~/.ssh/akshitahluwalia-personal

# Command Template
cd developer/trading-strategies/ && \
source env/bin/activate && \
python accumulator_v2.py \
--token="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2NjkzNTFmYmNiODFjYzFmODJjNTBkMmMiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIwOTMwODExLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjA5OTQ0MDB9.tjC36lG0aRwEnKWWQcdW2cQuBYE77J8B-LRBxHYtcFA" \
--lots="10" \
--option="PE" \
--underlying="NSE_INDEX|Nifty Bank" \
--instrumentmasterpath="instruments.csv" \
--expiry="2024-07-16"