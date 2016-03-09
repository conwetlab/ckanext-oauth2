#!/bin/bash
set -xe
trap 'jobs -p | xargs --no-run-if-empty kill' INT TERM EXIT

export PATH=$PATH:/usr/local/bin
export PIP_DOWNLOAD_CACHE=~/.pip_cache

WD=`pwd`
DB_HOST_IP=${DB_HOST_IP:=127.0.0.1}
POSTGRES_PORT=${POSTGRES_PORT:=5432}

echo "Downloading CKAN..."
git clone https://github.com/ckan/ckan
cd ckan
git checkout release-v2.5.2
cd $WD


echo "Checking Solr..."
SOLR_ACTIVE=`nc -z localhost 8983; echo $?`

if [ $SOLR_ACTIVE -ne 0 ]
then
    
    echo "Downloading Solr..."
    CACHE_DIR=~/.cache
    FILE=solr-4.8.1.tgz
    SOLAR_UNZIP_FOLDER=solr-4.8.1

    # If the solar folder does not exist, we have to build it
    if [ ! -d "$CACHE_DIR/$SOLAR_UNZIP_FOLDER" ]
    then
        # Download the solar installation file if it does not exist
        wget --no-verbose --timestamping --directory-prefix=$CACHE_DIR https://archive.apache.org/dist/lucene/solr/4.8.1/$FILE

        # Unzip the folder
        tar -xf "$CACHE_DIR/$FILE" --directory "$CACHE_DIR"

        # Delete the downloaded tar.gz
        rm "$CACHE_DIR/$FILE"
    fi
    
    echo "Configuring and starting Solr..."
    ln -s "$CACHE_DIR/$SOLAR_UNZIP_FOLDER" .
    mv "$SOLAR_UNZIP_FOLDER/example/solr/collection1/conf/schema.xml"  "$SOLAR_UNZIP_FOLDER/example/solr/collection1/conf/schema.xml.bak"
    ln -s $WD/ckan/ckan/config/solr/schema.xml "$SOLAR_UNZIP_FOLDER/example/solr/collection1/conf/schema.xml"
    cd solr-4.8.1/example
    java -jar start.jar 2>&1 > /dev/null &
    cd $WD

else
    echo "Solar is already installed..."
fi


echo "Setting up virtualenv..."
virtualenv --no-site-packages virtualenv
source virtualenv/bin/activate
pip install --upgrade pip


echo "Installing CKAN dependencies..."
cd ckan
python setup.py develop
pip install -r requirements.txt
pip install -r dev-requirements.txt
cd ..


echo "Removing databases from old executions..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS datastore_test;"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS ckan_test;"
sudo -u postgres psql -c "DROP USER IF EXISTS ckan_default;"


echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c "CREATE DATABASE ckan_test WITH OWNER ckan_default;"
sudo -u postgres psql -c "CREATE DATABASE datastore_test WITH OWNER ckan_default;"


echo "Modifying the configuration to setup properly the Postgres port..."
mkdir -p data/storage
echo "
sqlalchemy.url = postgresql://ckan_default:pass@$DB_HOST_IP:$POSTGRES_PORT/ckan_test
ckan.datastore.write_url = postgresql://ckan_default:pass@$DB_HOST_IP:$POSTGRES_PORT/datastore_test
ckan.datastore.read_url = postgresql://datastore_default:pass@$DB_HOST_IP:$POSTGRES_PORT/datastore_test

ckan.storage_path=data/storage" >> test.ini


echo "Initializing the database..."
sed -i "s/\(postgresql:\/\/.\+\)@localhost\(:[0-9]\+\)\?/\1@$DB_HOST_IP:$POSTGRES_PORT/g" ckan/test-core.ini
cd ckan
paster db init -c test-core.ini
cd ..


echo "Installing ckanext-oauth2 and its requirements..."
python setup.py develop


echo "Running tests..."
python setup.py nosetests