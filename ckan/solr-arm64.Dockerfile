# Dockerfile for Solr with CKAN schema versioned in this repo
FROM solr:8

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/solr/server/solr/configsets/ckan/conf \
    && cp /opt/solr/server/solr/configsets/_default/conf/solrconfig.xml /opt/solr/server/solr/configsets/ckan/conf/solrconfig.xml \
    && cp /opt/solr/server/solr/configsets/_default/conf/stopwords.txt /opt/solr/server/solr/configsets/ckan/conf/stopwords.txt \
    && cp /opt/solr/server/solr/configsets/_default/conf/synonyms.txt /opt/solr/server/solr/configsets/ckan/conf/synonyms.txt \
    && cp /opt/solr/server/solr/configsets/_default/conf/protwords.txt /opt/solr/server/solr/configsets/ckan/conf/protwords.txt

COPY ckan-solr-config/schema.xml /opt/solr/server/solr/configsets/ckan/conf/schema.xml

USER solr
