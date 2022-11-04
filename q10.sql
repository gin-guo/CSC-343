-- Rainmakers.

-- You must not change the next 2 lines or the table definition.
SET SEARCH_PATH TO uber, public;
DROP TABLE IF EXISTS q10 CASCADE;

CREATE TABLE q10(
    driver_id INTEGER,
    month CHAR(2),
    mileage_2020 FLOAT,
    billings_2020 FLOAT,
    mileage_2021 FLOAT,
    billings_2021 FLOAT,
    mileage_increase FLOAT,
    billings_increase FLOAT
);

-- Do this for each of the views that define your intermediate steps.  
-- (But give them better names!) The IF EXISTS avoids generating an error 
-- the first time this file is imported.
DROP VIEW IF EXISTS monthly CASCADE;
DROP VIEW IF EXISTS monthly_dist CASCADE;
DROP VIEW IF EXISTS all_months CASCADE;


-- Define views for your intermediate steps here:
CREATE VIEW monthly AS -- find mileage monthly
select distinct(Driver.driver_id), to_number(to_char(generate_series(1, 12), 'FM09'), 'FM09')::int AS month
from Driver, ClockedIn, Dispatch, Request
where Driver.driver_id = ClockedIn.driver_id
    and ClockedIn.shift_id = Dispatch.shift_id
    and Dispatch.request_id = Request.request_id
order by Driver.driver_id, month;

CREATE VIEW monthly_dist_2020 AS
select Driver.driver_id, EXTRACT(month from date(Request.datetime)) as month, 
            avg(source <@> destination) as mileage_2020, sum(amount) as billings_2020
        from Driver, ClockedIn, Dispatch, Request, Dropoff, Billed
        where Driver.driver_id = ClockedIn.driver_id
            and ClockedIn.shift_id = Dispatch.shift_id
            and Dispatch.request_id = Request.request_id
            and Request.request_id = Dropoff.request_id -- completed rides
            and Request.request_id = Billed.request_id -- billed rides
            and EXTRACT(year from date(Request.datetime)) = 2020
            group by Driver.driver_id, month;

CREATE VIEW all_months_2020 AS
select monthly.driver_id, monthly.month, 
    case when mileage_2020 is null then 0 else mileage_2020 end, 
    case when billings_2020 is null then 0 else billings_2020 end
from monthly left join monthly_dist_2020
    on monthly.month = monthly_dist_2020.month 
        and monthly.driver_id = monthly_dist_2020.driver_id;

CREATE VIEW monthly_dist_2021 AS
select Driver.driver_id, EXTRACT(month from date(Request.datetime)) as month, 
            avg(source <@> destination) as mileage_2021, sum(amount) as billings_2021
        from Driver, ClockedIn, Dispatch, Request, Dropoff, Billed
        where Driver.driver_id = ClockedIn.driver_id
            and ClockedIn.shift_id = Dispatch.shift_id
            and Dispatch.request_id = Request.request_id
            and Request.request_id = Dropoff.request_id -- completed rides
            and Request.request_id = Billed.request_id -- billed rides
            and EXTRACT(year from date(Request.datetime)) = 2021
            group by Driver.driver_id, month;

CREATE VIEW all_months_2021 AS
select monthly.driver_id, monthly.month, 
    case when mileage_2021 is null then 0 else mileage_2021 end, 
    case when billings_2021 is null then 0 else billings_2021 end
from monthly left join monthly_dist_2021 
    on monthly.month = monthly_dist_2021.month 
        and monthly.driver_id = monthly_dist_2021.driver_id;

-- Your query that answers the question goes below the "insert into" line:
INSERT INTO q10
select all_months_2020.driver_id, all_months_2020.month, 
    mileage_2020, billings_2020, mileage_2021, billings_2021,
    (mileage_2021 - mileage_2020) as mileage_increase,
    (billings_2021 - billings_2020) as billings_increase
from all_months_2020, all_months_2021
where all_months_2020.driver_id = all_months_2021.driver_id
    and all_months_2020.month = all_months_2021.month;
