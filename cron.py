import datetime
from schedule import every, repeat, run_pending
import time

from tortoise import run_async

from populate import run

@repeat(every().hour)
def job():
    print("-- Start cron " + datetime.datetime.now().isoformat())
    run_async(run(1, False))

while True:
    run_pending()
    time.sleep(1)