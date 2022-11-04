-- Lure them back.

-- You must not change the next 2 lines or the table definition.
SET SEARCH_PATH TO uber, public;
DROP TABLE IF EXISTS q2 CASCADE;

CREATE TABLE q2(
    client_id INTEGER,
    name VARCHAR(41),
  	email VARCHAR(30),
  	billed FLOAT,
  	decline INTEGER
);

-- Do this for each of the views that define your intermediate steps.  
-- (But give them better names!) The IF EXISTS avoids generating an error 
-- the first time this file is imported.
DROP VIEW IF EXISTS frequent_riders CASCADE;
DROP VIEW IF EXISTS past_rides CASCADE;
DROP VIEW IF EXISTS new_rides CASCADE;


-- Define views for your intermediate steps here:

CREATE VIEW frequent_riders AS -- find clients who had rides before 2020
select client_id, sum(amount) as billed
from
(select Client.client_id, amount, datetime
from Client, Billed, Request
where Client.client_id = Request.client_id
	and Billed.request_id = Request.request_id	
	and datetime < '2021-01-01'::date) AS a
group by client_id
having sum(amount) >= 500; -- costing at least $500 in total 


CREATE VIEW past_rides AS -- find clients with 1-10 rides (inclusive)
select frequent_riders.client_id, billed, count(frequent_riders.client_id) as num_past_rides
from frequent_riders, Request
where frequent_riders.client_id = Request.client_id
	and datetime between '2020-01-01'::date and '2020-12-30'::date -- in only 2020
group by frequent_riders.client_id, billed
having count(frequent_riders.client_id) between 1 and 10;


CREATE VIEW new_rides AS -- find clients with fewer rides in 2021 than in 2020
select Client.client_id, billed, num_past_rides, count(Client.client_id) as num_new_rides
from past_rides, Client, Request
where past_rides.client_id = Client.client_id
	and Client.client_id = Request.client_id
	and datetime between '2021-01-01'::date and '2021-12-30'::date
group by Client.client_id, num_past_rides, billed
having count(Client.client_id) < num_past_rides;


-- Your query that answers the question goes below the "insert into" line:
INSERT INTO q2
select new_rides.client_id, CONCAT(firstname, ' ', surname) as name, 
	email, billed, (num_past_rides - num_new_rides) as decline
from new_rides, Client
where new_rides.client_id = Client.client_id;