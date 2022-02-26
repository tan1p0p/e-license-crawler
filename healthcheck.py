import datetime

with open('healthcheck.log', 'a') as f:
    f.write(f'{datetime.datetime.now()}: cron running!!\n')
