-- Do drivers improve?

-- You must not change the next 2 lines or the table definition.
SET SEARCH_PATH TO uber, public;
DROP TABLE IF EXISTS q4 CASCADE;

CREATE TABLE q4(
    type VARCHAR(9),
    number INTEGER,
    early FLOAT,
    late FLOAT
);

-- Do this for each of the views that define your intermediate steps.  
-- (But give them better names!) The IF EXISTS avoids generating an error 
-- the first time this file is imported.
DROP VIEW IF EXISTS new_driver CASCADE;
DROP VIEW IF EXISTS driver_first_days CASCADE;

DROP VIEW IF EXISTS early CASCADE;
DROP VIEW IF EXISTS early_avg CASCADE;
DROP VIEW IF EXISTS late CASCADE;
DROP VIEW IF EXISTS late_avg CASCADE;

DROP VIEW IF EXISTS total_early_avg CASCADE;


-- Define views for your intermediate steps here:
CREATE VIEW new_driver AS -- consider drivers who have given a ride (one or more)
select Driver.driver_id, trained, DATE(Request.datetime)
from Driver, ClockedIn, Dispatch, Request
where Driver.driver_id = ClockedIn.driver_id
    and ClockedIn.shift_id = Dispatch.shift_id
    and Dispatch.request_id = Request.request_id;

CREATE VIEW driver_first_days AS -- consider drivers who have given a ride (one or more)
select a.driver_id, date
from (select driver_id, count(distinct(date))   --   on at least 10 different days
        from new_driver
        where trained = 'true'
        group by driver_id
        having count(distinct(date)) > 10) as a, new_driver
where a.driver_id = new_driver.driver_id;

-- select a.driver_id, date
-- from (select driver_id, count(distinct(date))  
--         from new_driver
--         group by driver_id
--         having count(distinct(date)) > 2) as a, new_driver
-- where a.driver_id = new_driver.driver_id;


CREATE VIEW early AS -- find first 5 days of job
select *
from (select ROW_NUMBER() over (
            PARTITION BY new_driver.driver_id 
            order by date AS r, driver_id, date
        from new_driver, driver_first_days
        where new_driver.driver_id = driver_first_days.driver_id;
    ) x
where x.r <= 5;

-- select *
-- from (select ROW_NUMBER() over (PARTITION BY driver_id order by date) AS r,
--         driver_id, date
--         from new_driver
--         where trained = 'true') x
-- where x.r <= 3;

CREATE VIEW early_avg AS  -- find average rating of first 5 days
select early.driver_id, avg(rating)
from early, ClockedIn, Dispatch, DriverRating
where early.driver_id = ClockedIn.driver_id
    and ClockedIn.shift_id = Dispatch.shift_id
    and Dispatch.request_id = DriverRating.request_id
group by early.driver_id;


-- select early.driver_id, avg(rating)
-- from early, ClockedIn, Dispatch, DriverRating
-- where early.driver_id = ClockedIn.driver_id
--     and ClockedIn.shift_id = Dispatch.shift_id
--     and Dispatch.request_id = DriverRating.request_id
-- group by early.driver_id;


CREATE VIEW late AS -- find days after first 5 days of job
select driver_id, date
from driver_first_days as b
where not exists (select driver_id, date from trained_early as a
                    where a.driver_id = b.driver_id
                    and a.date = b.date);


-- select driver_id, date from new_driver as b
-- where not exists (select driver_id, date from first as a 
--                     where a.driver_id = b.driver_id 
--                     and a.date = b.date);


CREATE VIEW late_avg AS  -- find average rating after first 5 days
select late.driver_id, avg(rating)
from late, ClockedIn, Dispatch, DriverRating
where late.driver_id = ClockedIn.driver_id
    and ClockedIn.shift_id = Dispatch.shift_id
    and Dispatch.request_id = DriverRating.request_id
group by late.driver_id;


CREATE VIEW total_early_avg AS -- calculate average of early averages
select trained, count(avg), avg(avg) as early
from Driver, early_avg
where Driver.driver_id = early_avg.driver_id
group by trained;


CREATE VIEW total_late_avg AS -- calculate average of late averages
select trained, avg(avg) as late
from Driver, late_avg
where Driver.driver_id = late_avg.driver_id
group by trained;


-- Your query that answers the question goes below the "insert into" line:
INSERT INTO q4
select total_early_avg.trained as type, n.count as number, early, late
from (select trained, count(distinct(driver_id))
        from driver_first_days
        group by trained) as n, total_early_avg, total_late_avg;

