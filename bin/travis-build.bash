#!/usr/bin/env bash

set -e

function test_connection {
    echo "Testing $1 connection"

    attempt_counter=0
    max_attempts=50

    until $(curl --output /dev/null --silent --head --fail --insecure $2); do
        if [ ${attempt_counter} -eq ${max_attempts} ];then
            echo "Max attempts reached"
            exit 1
        fi

        attempt_counter=$(($attempt_counter+1))
        sleep 5
    done

    echo "$1 connection, OK"
}

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get clean
sudo rm -r /var/lib/apt/lists/*

sudo apt-get update -qq
sudo apt-get install solr-jetty

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
cd ckan
git checkout ckan-$CKANVERSION
python setup.py develop

sed -i "s|psycopg2==2.4.5|psycopg2==2.7.1|g" requirements.txt

pip install -r requirements.txt --allow-all-external
pip install -r dev-requirements.txt --allow-all-external
cd -

echo "Setting up Solr..."
# solr is multicore for tests on ckan master now, but it's easier to run tests
# on Travis single-core still.
# see https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini
printf "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty restart

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c "CREATE USER datastore_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c "CREATE DATABASE ckan_test WITH OWNER ckan_default;"
sudo -u postgres psql -c "CREATE DATABASE datastore_test WITH OWNER ckan_default;"

echo "Initialising the database..."
cd ckan
paster db init -c test-core.ini
cd -

echo "Installing ckanext-oauth2 and its requirements..."
python setup.py develop

if [ "$INTEGRATION_TEST" = "true" ]; then
        sudo sh -c 'echo "\n[ SAN ]\nsubjectAltName=DNS:localhost" >> /etc/ssl/openssl.cnf'
        sudo openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
            -subj '/O=API Umbrella/CN=localhost' \
            -keyout /etc/ssl/self_signed.key -out /usr/local/share/ca-certificates/self_signed.crt \
            -reqexts SAN -extensions SAN

        sudo update-ca-certificates
        export REQUESTS_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt"

        docker network create main
        cd ${TRAVIS_BUILD_DIR}/ci

        docker-compose up -d
        cd ..

        # Wait until idm is ready
        test_connection 'KeyRock' http://localhost:3000
fi

echo "travis-build.bash is done."
