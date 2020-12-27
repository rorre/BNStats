<p align="center">
<img src="https://raw.githubusercontent.com/rorre/BNStats/master/bnstats/root/ms-icon-144x144.png" alt="BNStats logo.">
</p>
<h2 align="center">BN Stats site</h2>

## Requirements
- Python 3.8+
- Poetry
- PostgresQL (Other DB is supported, but it's a pain in the ass to migrate as `aerich` makes it not flexible.)

## Running
- Clone the repo
- Have these on your environment variable or in `.env` file
```
DEBUG=<bool>
SECRET=<str>
API_KEY=<str>
BNSITE_SESSION=<str>
DB_URL=<str>
```
- Install the repo with poetry
```sh
poetry install [--no-dev]
```
- Populate the database
```sh
poetry run aerich upgrade
poetry run python populate.py
# or
poetry shell
aerich upgrade
python populate.py
```
- Run it.
```sh
poetry run uvicorn bnstats:app
# or
poetry shell
uvicorn bnstats:app
# or, if you want to use gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker bnstats:app
```
- Run cronjob every 1-2 hours.

`cron.sh`
```sh
cd <PathToProject>
<PoetryEnv>/bin/python <PathToProject>/populate.py -d 1
```

`crontab`
```
# Every 30 minutes
*/30 * * * * cron.sh
````

## Deploying
Look at [Uvicorn's deployment docs](https://www.uvicorn.org/deployment/).

## TODOs
- ~~Find and delete kicked BNs when the listing changes~~
- ~~Star rating graph + label + avg~~
- ~~Specific timespan option~~
- ~~Move database update routine out of application~~
- ~~Scoring system~~
- Update tests
