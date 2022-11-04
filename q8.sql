-- Scratching backs?

-- You must not change the next 2 lines or the table definition.
SET SEARCH_PATH TO uber, public;
DROP TABLE IF EXISTS q8 CASCADE;

CREATE TABLE q8(
    client_id INTEGER,
    reciprocals INTEGER,
    difference FLOAT
);

-- Do this for each of the views that define your intermediate steps.  
-- (But give them better names!) The IF EXISTS avoids generating an error 
-- the first time this file is imported.
DROP VIEW IF EXISTS recip_ratings CASCADE;
DROP VIEW IF EXISTS num_recips CASCADE;


-- Define views for your intermediate steps here:
CREATE VIEW recip_ratings as -- find request_id that have both driver and client ratings 
select Client.client_id, DriverRating.request_id, 
        DriverRating.rating as d_rating, ClientRating.rating as c_rating
from Client, Request, Driver, ClockedIn, Dispatch, DriverRating, ClientRating
where Client.client_id = Request.client_id
    and Request.request_id = ClientRating.request_id
    and Driver.driver_id = ClockedIn.driver_id
    and ClockedIn.shift_id = Dispatch.shift_id
    and Dispatch.request_id = DriverRating.request_id
    and DriverRating.request_id = ClientRating.request_id;


CREATE VIEW num_recips as -- find number of reciprocals and rating difference 
select a.client_id, a.count as reciprocals, (d_rating-c_rating) as difference
from (select client_id, count(client_id)
        from recip_ratings
        group by client_id)as a, recip_ratings
where a.client_id = recip_ratings.client_id;

-- Your query that answers the question goes below the "insert into" line:
INSERT INTO q8
select client_id, reciprocals, avg(difference)
from num_recips
group by client_id, reciprocals;