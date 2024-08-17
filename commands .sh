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
python scalper.py \
--token="" \
--lots="5" \
--option="PE" \
--underlying="NSE_INDEX|Nifty Bank" \
--instrumentmasterpath="instruments.csv" \
--expiry="2024-07-24"