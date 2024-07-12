# Command Template

cd developer/trading-strategies/ && \
source env/bin/activate && \
python accumulator_v2.py \
--token="ABC" \
--lots="2" \
--option="CE" \
--underlying="BANKNIFTY" \
--instrumentmasterpath="instruments.csv" \
--expiry="2024-07-16"