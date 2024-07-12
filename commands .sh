cd developer/trading-strategies/ && source env/bin/activate

eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2NjkwYWEyMmVkY2E3MTI1NzQ1MmE1M2UiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIwNzU2NzcwLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjA4MjE2MDB9.iQdMKASMOzyze4UbtCSX4iIQQ4dWVLe6b0i7lmRC6Jw

python supertrend.py --numberoflots=1 --lotsize=15 --accesstoken="" --instrument=""


# Accumulator Call
cd developer/trading-strategies/ && source env/bin/activate && python accumulator.py --numberoflots=5 --lotsize=15 --accesstoken="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2NjkwYWEyMmVkY2E3MTI1NzQ1MmE1M2UiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIwNzU2NzcwLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjA4MjE2MDB9.iQdMKASMOzyze4UbtCSX4iIQQ4dWVLe6b0i7lmRC6Jw" --instrument="NSE_FO|37027" > ./logs/acc-call.log
# Accumulator Put
cd developer/trading-strategies/ && source env/bin/activate && python accumulator.py --numberoflots=5 --lotsize=15 --accesstoken="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2NjkwYWEyMmVkY2E3MTI1NzQ1MmE1M2UiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIwNzU2NzcwLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjA4MjE2MDB9.iQdMKASMOzyze4UbtCSX4iIQQ4dWVLe6b0i7lmRC6Jw" --instrument="NSE_FO|37026" > ./logs/acc-put.log