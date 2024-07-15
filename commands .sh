eval "$(ssh-agent -s)" && ssh-add ~/.ssh/akshitahluwalia-personal

# Command Template
cd developer/trading-strategies/ && \
source env/bin/activate && \
python accumulator_v2.py \
--token="" \
--lots="20" \
--option="CE" \
--underlying="NSE_INDEX|Nifty Bank" \
--instrumentmasterpath="instruments.csv" \
--expiry="2024-07-16"

cd developer/trading-strategies/ && \
source env/bin/activate && \
python accumulator_v2.py \
--token="" \
--lots="20" \
--option="CE" \
--underlying="NSE_INDEX|Nifty Bank" \
--instrumentmasterpath="instruments.csv" \
--expiry="2024-07-16"

cd developer/trading-strategies/ && \
source env/bin/activate && \
python accumulator_v2.py \
--token="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2Njk0OWY5M2NiODFjYzFmODJjNTI3YzEiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIxMDE2MjExLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjEwODA4MDB9.sBLyXyBhiJE1F1598NcVXqoV2ntzOIIcn2z6-bzQa00" \
--lots="10" \
--option="CE" \
--underlying="NSE_INDEX|Nifty Bank" \
--instrumentmasterpath="instruments.csv" \
--expiry="2024-07-16"

cd developer/trading-strategies/ && \
source env/bin/activate && \
python accumulator_v2.py \
--token="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2Njk0OWY5M2NiODFjYzFmODJjNTI3YzEiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIxMDE2MjExLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjEwODA4MDB9.sBLyXyBhiJE1F1598NcVXqoV2ntzOIIcn2z6-bzQa00" \
--lots="10" \
--option="PE" \
--underlying="NSE_INDEX|Nifty Bank" \
--instrumentmasterpath="instruments.csv" \
--expiry="2024-07-1




