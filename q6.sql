-- Frequent riders.

-- You must not change the next 2 lines or the table definition.
SET SEARCH_PATH TO uber, public;
DROP TABLE IF EXISTS q6 CASCADE;

CREATE TABLE q6(
    client_id INTEGER,
    year CHAR(4),
    rides INTEGER
);

-- Do this for each of the views that define your intermediate steps.  
-- (But give them better names!) The IF EXISTS avoids generating an error 
-- the first time this file is imported.
DROP VIEW IF EXISTS years CASCADE;
DROP VIEW IF EXISTS clients_yearly CASCADE;
DROP VIEW IF EXISTS all_clients CASCADE;
DROP VIEW IF EXISTS top_three CASCADE;
DROP VIEW IF EXISTS bot_three CASCADE;

-- Define views for your intermediate steps here:

CREATE VIEW years AS
select client_id, years.year
from (select distinct(EXTRACT(year from date(datetime))) as year
        from Client, Request
        where Client.client_id = Request.client_id
order by year) as years, Client;


CREATE VIEW clients_yearly AS -- get clients and their rides count each year
select client_id, year, count(year)
from (select Client.client_id, EXTRACT(year from date(datetime)) as year
        from Client, Request
        where Client.client_id = Request.client_id) as a
group by client_id, year;


CREATE VIEW all_clients AS
select years.client_id, years.year,
    case when count is null then 0 else count end
from years left join clients_yearly 
on years.client_id = clients_yearly.client_id
    and years.year = clients_yearly.year;


CREATE VIEW top_three AS -- find clients with highest 3 ride counts yearly
select client_id, year, count
from all_clients
where count in (select distinct(count)
    from all_clients
    order by count DESC
    limit 3);


CREATE VIEW bot_three AS -- find clients with lowest 3 ride counts yearly
select client_id, year, count
from all_clients
where count in (select distinct(count)
    from all_clients
    order by count ASC
    limit 3);


-- Your query that answers the question goes below the "insert into" line:
INSERT INTO q6
select client_id, year, count as rides
from top_three 
union
select client_id, year, count as rides
from bot_three
order by client_id;