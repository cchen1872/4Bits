#!/bin/bash

export FLASK_ENV=development
export PROJ_DIR=$PWD
export DEBUG=1
export MONGO_DB_USRNAME=nz2065
export MONGO_DB_PASSWORD=Cbf6EvI2pewBj8KM

# run our server locally:
PYTHONPATH=$(pwd):$PYTHONPATH
FLASK_APP=server.endpoints flask run --debug --host=127.0.0.1 --port=8000
