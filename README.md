<p align="center">
<img src="https://raw.githubusercontent.com/rorre/BNStats/master/bnstats/root/ms-icon-144x144.png" alt="BNStats logo.">
</p>
<h2 align="center">BN Stats site</h2>

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
poetry run python populate.py
# or
poetry shell
python populate.py
```
- Run it.
```sh
poetry run uvicorn bnstats:app
# or
poetry shell
uvicorn bnstats:app
```

## Deploying
Look at [Uvicorn's deployment docs](https://www.uvicorn.org/deployment/).

## TODOs
- Find and delete kicked BNs when the listing changes
- Star rating graph + label + avg
- Specific timespan option
