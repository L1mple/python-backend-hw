CREATE SCHEMA IF NOT EXISTS iso_lab;
SET search_path = iso_lab, public;

DROP TABLE IF EXISTS accounts       CASCADE;
DROP TABLE IF EXISTS orders         CASCADE;
DROP TABLE IF EXISTS doctors        CASCADE;
DROP TABLE IF EXISTS oncall         CASCADE;
