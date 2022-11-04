"""
Part2 of csc343 A2: Code that could be part of a ride-sharing application.
csc343, Fall 2022
University of Toronto

--------------------------------------------------------------------------------
This file is Copyright (c) 2022 Diane Horton and Marina Tawfik.
All forms of distribution, whether as given or with any changes, are
expressly prohibited.
--------------------------------------------------------------------------------
"""
import psycopg2 as pg
import psycopg2.extensions as pg_ext
from typing import Optional, List, Any
from datetime import datetime
import re


class GeoLoc:
    """A geographic location.

    === Instance Attributes ===
    longitude: the angular distance of this GeoLoc, east or west of the prime
        meridian.
    latitude: the angular distance of this GeoLoc, north or south of the
        Earth's equator.

    === Representation Invariants ===
    - longitude is in the closed interval [-180.0, 180.0]
    - latitude is in the closed interval [-90.0, 90.0]

    >>> where = GeoLoc(-25.0, 50.0)
    >>> where.longitude
    -25.0
    >>> where.latitude
    50.0
    """
    longitude: float
    latitude: float

    def __init__(self, longitude: float, latitude: float) -> None:
        """Initialize this geographic location with longitude <longitude> and
        latitude <latitude>.
        """
        self.longitude = longitude
        self.latitude = latitude

        assert -180.0 <= longitude <= 180.0, \
            f"Invalid value for longitude: {longitude}"
        assert -90.0 <= latitude <= 90.0, \
            f"Invalid value for latitude: {latitude}"


class Assignment2:
    """A class that can work with data conforming to the schema in schema.ddl.

    === Instance Attributes ===
    connection: connection to a PostgreSQL database of ride-sharing information.

    Representation invariants:
    - The database to which connection is established conforms to the schema
      in schema.ddl.
    """
    connection: Optional[pg_ext.connection]

    def __init__(self) -> None:
        """Initialize this Assignment2 instance, with no database connection
        yet.
        """
        self.connection = pg.connect(dbname = "csc343h-tungcarm", user = "tungcarm", password = "", options = "-c search_path=uber,public")

    def connect(self, dbname: str, username: str, password: str) -> bool:
        """Establish a connection to the database <dbname> using the
        username <username> and password <password>, and assign it to the
        instance attribute <connection>. In addition, set the search path to
        uber, public.

        Return True if the connection was made successfully, False otherwise.
        I.e., do NOT throw an error if making the connection fails.

        >>> a2 = Assignment2()
        >>> # This example will work for you if you change the arguments as
        >>> # appropriate for your account.
        >>> a2.connect("csc343h-dianeh", "dianeh", "")
        True
        >>> # In this example, the connection cannot be made.
        >>> a2.connect("nonsense", "silly", "junk")
        False
        """
        try:
            self.connection = pg.connect(
                dbname=dbname, user=username, password=password,
                options="-c search_path=uber,public"
            )
            # This allows psycopg2 to learn about our custom type geo_loc.
            self._register_geo_loc()
            return True
        except pg.Error:
            return False

    def disconnect(self) -> bool:
        """Close the database connection.

        Return True if closing the connection was successful, False otherwise.
        I.e., do NOT throw an error if closing the connection failed.

        >>> a2 = Assignment2()
        >>> # This example will work for you if you change the arguments as
        >>> # appropriate for your account.
        >>> a2.connect("csc343h-dianeh", "dianeh", "")
        True
        >>> a2.disconnect()
        True
        >>> a2.disconnect()
        False
        """
        try:
            if not self.connection.closed:
                self.connection.close()
            return True
        except pg.Error:
            return False
    
    # ======================= Helper methods ======================= #
    def ongoing_drivers(self, driver_id: int) -> bool:
        """Return whether a given driver is on a shift. 
        """
        cursor = self.connection.cursor()
        cursor.execute("""SET SEARCH_PATH TO uber, public;""")
        get_ongoing_drivers = """SELECT driver_id FROM ClockedIn LEFT JOIN ClockedOut USING(shift_id) WHERE ClockedOut.datetime IS NULL;"""
        cursor.execute(get_ongoing_drivers)
        for driver in cursor:
                if int(driver[0]) == driver_id:
                    cursor.close()
                    return True
        cursor.close()
        return False
    
    def real_drivers(self, driver_id: int) -> bool:
        """Return whether a given driver exists 
        """
        cursor = self.connection.cursor()
        cursor.execute("""SET SEARCH_PATH TO uber, public;""")
        get_real_drivers = """SELECT driver_id FROM ClockedIn;"""
        cursor.execute(get_real_drivers)
        for driver in cursor:
                if int(driver[0]) == driver_id:
                    cursor.close()
                    return True
        cursor.close()
        return False
    
    def real_client(self, client_id: int) -> bool:
        """Return whether a given client exists 
        """
        cursor = self.connection.cursor()
        cursor.execute("""SET SEARCH_PATH TO uber, public;""")
        get_real_client = """SELECT client_id FROM Request;"""
        cursor.execute(get_real_client)
        for client in cursor:
                if int(client[0]) == client_id:
                    cursor.close()
                    return True
        cursor.close()
        return False
    
    def dispatched_drivers(self, driver_id: int, client_id: int) -> tuple:
        """Return whether the given driver has been dispatched to
        pick up the client.
        """
        cursor = self.connection.cursor()
        cursor.execute("""SET SEARCH_PATH TO uber, public;""")
        cursor.execute("""DROP VIEW IF EXISTS valid_requests CASCADE;""")
        get_valid_requests = """CREATE VIEW valid_requests AS
        (SELECT request_id FROM Dispatch) EXCEPT ALL (SELECT request_id FROM Pickup);
        """
        cursor.execute(get_valid_requests)

        get_dispatched_drivers = """
        SELECT driver_id, client_id, request_id
        FROM Dispatch NATURAL JOIN valid_requests JOIN Request USING(request_id) JOIN ClockedIn USING(shift_id) JOIN Driver USING(driver_id) JOIN Client USING(client_id);
        """
        cursor.execute(get_dispatched_drivers)
        for pair in cursor:
            if int(pair[0]) == driver_id and int(pair[1]) == client_id:
                cursor.close()
                return int(pair[2]), True
        cursor.close()
        return -1, False

    def picked_up_driver(self, driver_id: int, client_id: int):
        """Return whether the driver has picked up the client.
        """
        cursor = self.connection.cursor()
        cursor.execute("""SET SEARCH_PATH TO uber, public;""")
        get_pickedup = """
        SELECT request_id
        FROM Pickup JOIN Dispatch USING(request_id);
        """
        cursor.execute(get_pickedup)
        dispatch_info = self.dispatched_drivers(driver_id, client_id)
        for request_id in cursor:
            if request_id == dispatch_info[0]:
                cursor.close()
                return True
        cursor.close()
        return False

    def clients_within_bounds(self, nw: GeoLoc, se: GeoLoc) -> list:
        """Return clients that are within the given bounds and 
        have not had a ride dispatched for them. Test with data2
        """
        cursor = self.connection.cursor()
        cursor.execute("""SET SEARCH_PATH TO uber, public;""")
        cursor.execute("""DROP VIEW IF EXISTS open_requests CASCADE;""")
        print('hi')
        get_open_requests="""
        CREATE VIEW open_requests AS
        (SELECT request_id
        FROM Request) EXCEPT ALL
        (SELECT request_id
        FROM Dispatch);
        """
        cursor.execute(get_open_requests)
        sorted_requests="""
        SELECT *
        FROM Request NATURAL JOIN open_requests; 
        """
        cursor.execute(sorted_requests)
        print(cursor)
        client_list = []
        for client in cursor:
            # print(float(client[3].longitude))
            # print(float(client[3].latitude))
            # print(float(nw.longitude))
            # print(float(nw.latitude))
            # print(float(se.longitude))
            # print(float(se.latitude))
            if float(client[3].longitude) <= se.longitude and \
            float(client[3].longitude) >= nw.longitude and \
            float(client[3].latitude) <= nw.latitude and \
            float(client[3].latitude) >= se.latitude:
                client_list.append(client)
        cursor.close()
        print(client_list)

        return client_list
    
    def client_billed_totals(self, client_list: list) -> list:
        """Sort the clients based on their previous billed totals
        """
        cursor = self.connection.cursor()
        cursor.execute("""SET SEARCH_PATH TO uber, public;""")
        # cursor.execute("""DROP VIEW IF EXISTS client_bills CASCADE;""")
        client_bills="""
        SELECT client_id, sum(amount)
        FROM Request NATURAL JOIN Billed
        GROUP BY client_id
        ORDER BY sum(amount) DESC;
        """

        client_sorted = {}
        cursor.execute(client_bills)
        for client in cursor:
            client_sorted[client[0]] = client[1]
        
        client_sorted_total = []
        for client in client_list:
            if client[1] in client_sorted:
                client_sorted_total.append((client, float(client_sorted[client[1]])))
            else:
                client_sorted_total.append((client, float(0)))
        
        client_sorted_total = sorted(client_sorted_total, key=lambda x: x[1])
        # client_sorted_total = ([request_id, client_id, datetime, source, destination], amount)
        cursor.close()
        print(client_sorted_total)
        return client_sorted_total


    def valid_drivers(self, nw: GeoLoc, se: GeoLoc) -> list:
        cursor = self.connection.cursor()
        cursor.execute("""SET SEARCH_PATH TO uber, public;""")
        cursor.execute("""DROP VIEW IF EXISTS ongoing_drivers CASCADE;""")
        ongoing_drivers_view = """
        CREATE VIEW ongoing_drivers AS
        SELECT driver_id, shift_id
        FROM ClockedIn LEFT JOIN ClockedOut USING(shift_id)
        WHERE ClockedOut.datetime IS NULL;
        """
        cursor.execute(ongoing_drivers_view)
        cursor.execute("""DROP VIEW IF EXISTS non_driving_drivers CASCADE;""")
        get_driving_drivers = """
        CREATE VIEW non_driving_drivers AS
        (SELECT shift_id
        FROM ClockedIn) EXCEPT ALL 
        (SELECT shift_id
        FROM Dispatch NATURAL JOIN
        ((SELECT request_id
        FROM Dispatch) EXCEPT ALL
        (SELECT request_id
        FROM Dispatch JOIN Pickup USING(request_id) JOIN Dropoff USING(request_id))) Temp);
        """
        cursor.execute(get_driving_drivers)
        cursor.execute("""DROP VIEW IF EXISTS recent_drivers CASCADE;""")
        get_recent_drivers="""
        CREATE VIEW recent_drivers AS
        SELECT Location.shift_id, location
        FROM LOCATION JOIN 
        (SELECT shift_id, max(datetime)
        FROM Location
        GROUP BY shift_id) Temp
        ON Temp.max = Location.datetime AND Location.shift_id = Temp.shift_id;
        """
        cursor.execute(get_recent_drivers)
        valid_drivers="""
        SELECT driver_id, shift_id, location
        FROM recent_drivers NATURAL JOIN ongoing_drivers NATURAL JOIN non_driving_drivers;
        """
        cursor.execute(valid_drivers)
        driver_list = []
        for driver in cursor:
            if float(driver[2].longitude) <= se.longitude and \
            float(driver[2].longitude) >= nw.longitude and \
            float(driver[2].latitude) <= nw.latitude and \
            float(driver[2].latitude) >= se.latitude:
                driver_list.append(driver)
        print(driver_list)
        cursor.close()
        return driver_list




    # ======================= Driver-related methods ======================= #

    def clock_in(self, driver_id: int, when: datetime, geo_loc: GeoLoc) -> bool:
        """Record the fact that the driver with id <driver_id> has declared that
        they are available to start their shift at date time <when> and with
        starting location <geo_loc>. Do so by inserting a row in both the
        ClockedIn and the Location tables.

        If there are no rows are in the ClockedIn table, the id of the shift
        is 1. Otherwise, it is the maximum current shift id + 1.

        A driver can NOT start a new shift if they have an ongoing shift.

        Return True if clocking in was successful, False otherwise. I.e., do NOT
        throw an error if clocking in fails.

        Precondition:
            - <when> is after all dates currently recorded in the database.
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("""SET SEARCH_PATH TO uber, public;""")
            ongoing = self.ongoing_drivers(driver_id)
            exists = self.real_drivers(driver_id)

            if ongoing or not exists:
                cursor.close()
                return False
            else:
                get_max = """SELECT max(shift_id) FROM ClockedIn;"""
                cursor.execute(get_max)
                shift_id = int(cursor.fetchone()[0]) + 1
                when = when.replace(second = 0, microsecond = 0)
                cursor.execute("INSERT INTO ClockedIn VALUES (%s, %s, %s);", [shift_id, driver_id, when])
                cursor.execute("INSERT INTO Location VALUES (%s, %s, %s);", [shift_id, when, geo_loc])
                self.connection.commit()
                cursor.close()
                return True

            pass
        except pg.Error as ex:
            # You may find it helpful to uncomment this line while debugging,
            # as it will show you all the details of the error that occurred:
            raise ex
            return False

    def pick_up(self, driver_id: int, client_id: int, when: datetime) -> bool:
        """Record the fact that the driver with driver id <driver_id> has
        picked up the client with client id <client_id> at date time <when>.

        If (a) the driver is currently on an ongoing shift, and
           (b) they have been dispatched to pick up the client, and
           (c) the corresponding pick-up has not been recorded
        record it by adding a row to the Pickup table, and return True.
        Otherwise, return False.

        You may not assume that the dispatch actually occurred, but you may
        assume there is no more than one outstanding dispatch entry for this
        driver and this client.

        Return True if the operation was successful, False otherwise. I.e.,
        do NOT throw an error if this pick up fails.

        Precondition:
            - <when> is after all dates currently recorded in the database.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""SET SEARCH_PATH TO uber, public;""")
            d_exists = self.real_drivers(driver_id)
            c_exists = self.real_client(client_id)
            ongoing = self.ongoing_drivers(driver_id)
            dispatched = self.dispatched_drivers(driver_id, client_id)
            pickedup = self.picked_up_driver(driver_id, client_id)
            print(ongoing)
            if ongoing and d_exists and c_exists and dispatched[1]:
                when = when.replace(second = 0, microsecond = 0)
                cursor.execute("INSERT INTO Pickup VALUES (%s, %s)", [dispatched[0], when])
                self.connection.commit()
                cursor.close()
                return True
            else:
                cursor.close()
                return False
            pass
        except pg.Error as ex:
            # You may find it helpful to uncomment this line while debugging,
            # as it will show you all the details of the error that occurred:
            raise ex
            return False

    # ===================== Dispatcher-related methods ===================== #

    def dispatch(self, nw: GeoLoc, se: GeoLoc, when: datetime) -> None:
        """Dispatch drivers to the clients who have requested rides in the area
        bounded by <nw> and <se>, such that:
            - <nw> is the longitude and latitude in the northwest corner of this
            area
            - <se> is the longitude and latitude in the southeast corner of this
            area
        and record the dispatch time as <when>.

        Area boundaries are inclusive. For example, the point (4.0, 10.0)
        is considered within the area defined by
                    NW = (1.0, 10.0) and SE = (25.0, 2.0)
        even though it is right at the upper boundary of the area.

        NOTE: + longitude values decrease as we move further west, and
                latitude values decrease as we move further south.
              + You may find the PostgreSQL operators @> and <@> helpful.

        For all clients who have requested rides in this area (i.e., whose
        request has a source location in this area) and a driver has not
        been dispatched to them yet, dispatch drivers to them one at a time,
        from the client with the highest total billings down to the client
        with the lowest total billings, or until there are no more drivers
        available.

        Only drivers who meet all of these conditions are dispatched:
            (a) They are currently on an ongoing shift.
            (b) They are available and are NOT currently dispatched or on
            an ongoing ride.
            (c) Their most recent recorded location is in the area bounded by
            <nw> and <se>.
        When choosing a driver for a particular client, if there are several
        drivers to choose from, choose the one closest to the client's source
        location. In the case of a tie, any one of the tied drivers may be
        dispatched.

        Dispatching a driver is accomplished by adding a row to the Dispatch
        table. The dispatch car location is the driver's most recent recorded
        location. All dispatching that results from a call to this method is
        recorded to have happened at the same time, which is passed through
        parameter <when>.

        If an exception occurs during dispatch, rollback ALL changes.

        Precondition:
            - <when> is after all dates currently recorded in the database.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""SET SEARCH_PATH TO uber, public;""")
            clients = self.clients_within_bounds(nw, se)
            client_list = self.client_billed_totals(clients)
            driver_list = self.valid_drivers(nw, se)
            while client_list != [] and driver_list != []:
                client = client_list.pop()
                c_lat = client[0][3].latitude
                c_long = client[0][3].longitude
                min_d = float('inf')
                d = {}
                for driver in driver_list:
                    d_lat = driver[2].latitude
                    d_long = driver[2].longitude
                    distance = ((d_lat - c_lat)**2 + (d_long - c_long)**2)**(1/2)
                    if distance <= min_d:
                        min_d = distance
                        d[distance] = driver
                selected_driver = d[min_d]
                driver_list.remove(selected_driver)
                request_id = client[0][0]
                shift_id = selected_driver[1]
                car_location = selected_driver[2]
                datetime = when.replace(second = 0, microsecond = 0)
                cursor.execute("""INSERT INTO Dispatch VALUES (%s, %s, %s, %s)""", [request_id, shift_id, car_location, datetime])
            cursor.close()
            self.connection.commit()
            pass
        except pg.Error as ex:
            # You may find it helpful to uncomment this line while debugging,
            # as it will show you all the details of the error that occurred:
            self.connection.rollback()
            raise ex
            return

    # =======================     Helper methods     ======================= #

    # You do not need to understand this code. See the doctest example in
    # class GeoLoc (look for ">>>") for how to use class GeoLoc.

    def _register_geo_loc(self) -> None:
        """Register the GeoLoc type and create the GeoLoc type adapter.

        This method
            (1) informs psycopg2 that the Python class GeoLoc corresponds
                to geo_loc in PostgreSQL.
            (2) defines the logic for quoting GeoLoc objects so that you
                can use GeoLoc objects in calls to execute.
            (3) defines the logic of reading GeoLoc objects from PostgreSQL.

        DO NOT make any modifications to this method.
        """

        def adapt_geo_loc(loc: GeoLoc) -> pg_ext.AsIs:
            """Convert the given geographical location <loc> to a quoted
            SQL string.
            """
            longitude = pg_ext.adapt(loc.longitude)
            latitude = pg_ext.adapt(loc.latitude)
            return pg_ext.AsIs(f"'({longitude}, {latitude})'::geo_loc")

        def cast_geo_loc(value: Optional[str], *args: List[Any]) \
                -> Optional[GeoLoc]:
            """Convert the given value <value> to a GeoLoc object.

            Throw an InterfaceError if the given value can't be converted to
            a GeoLoc object.
            """
            if value is None:
                return None
            m = re.match(r"\(([^)]+),([^)]+)\)", value)

            if m:
                return GeoLoc(float(m.group(1)), float(m.group(2)))
            else:
                raise pg.InterfaceError(f"bad geo_loc representation: {value}")

        with self.connection, self.connection.cursor() as cursor:
            cursor.execute("SELECT NULL::geo_loc")
            geo_loc_oid = cursor.description[0][1]

            geo_loc_type = pg_ext.new_type(
                (geo_loc_oid,), "GeoLoc", cast_geo_loc
            )
            pg_ext.register_type(geo_loc_type)
            pg_ext.register_adapter(GeoLoc, adapt_geo_loc)


def clockin_test_function() -> None:
    """A sample test function."""
    a2 = Assignment2()
    try:
        # TODO: Change this to connect to your own database:
        connected = a2.connect("csc343h-tungcarm", "tungcarm", "")
        print(f"[Connected] Expected True | Got {connected}.")

        # TODO: Test one or more methods here, or better yet, make more testing
        #   functions, with each testing a different aspect of the code.

        # ------------------- Testing Clocked In -----------------------------#

        # These tests assume that you have already loaded the sample data we
        # provided into your database.

        # This driver doesn't exist in db
        clocked_in = a2.clock_in(
            989898, datetime.now(), GeoLoc(-79.233, 43.712)
        )
        print(f"[ClockIn] Expected False | Got {clocked_in}.")

        # This drive does exist in the db
        clocked_in = a2.clock_in(
            22222, datetime.now(), GeoLoc(-79.233, 43.712)
        )
        print(f"[ClockIn] Expected True | Got {clocked_in}.")

        # Same driver clocks in again
        clocked_in = a2.clock_in(
            22222, datetime.now(), GeoLoc(-79.233, 43.712)
        )
        print(f"[ClockIn] Expected False | Got {clocked_in}.")

    finally:
        a2.disconnect()

def pickup_test_function() -> None:
    """A sample test function."""
    a2 = Assignment2()
    try:
        # TODO: Change this to connect to your own database:
        connected = a2.connect("csc343h-tungcarm", "tungcarm", "")
        print(f"[Connected] Expected True | Got {connected}.")

        # TODO: Test one or more methods here, or better yet, make more testing
        #   functions, with each testing a different aspect of the code.

        # ------------------- Testing Clocked In -----------------------------#

        # These tests assume that you have already loaded the sample data we
        # provided into your database.

        # This driver doesn't exist in db
        picked_up = a2.pick_up(
            989898, 100, datetime.now()
        )
        print(f"[PickUp] Expected False | Got {picked_up}.")

        # This client doesn't exist in db
        picked_up = a2.pick_up(
            12345, 33, datetime.now()
        )
        print(f"[PickUp] Expected False | Got {picked_up}.")

        # Driver has already picked up.
        picked_up = a2.pick_up(
            12345, 99, datetime.now()
        )
        print(f"[PickUp] Expected False | Got {picked_up}.")

        # Should Work
        picked_up = a2.pick_up(
            22222, 100, datetime.now()
        )
        print(f"[PickUp] Expected True | Got {picked_up}.")

    finally:
        a2.disconnect()

def client_within_bounds_test_function() -> None:
    """A sample test function."""
    a2 = Assignment2()
    try:
        # TODO: Change this to connect to your own database:
        connected = a2.connect("csc343h-tungcarm", "tungcarm", "")
        print(f"[Connected] Expected True | Got {connected}.")

        # TODO: Test one or more methods here, or better yet, make more testing
        #   functions, with each testing a different aspect of the code.

        # ------------------- Testing Clocked In -----------------------------#

        # These tests assume that you have already loaded the sample data we
        # provided into your database.
        nw = GeoLoc(-5, 60)
        se = GeoLoc(10, 20)
        a2.clients_within_bounds(nw, se)
       
    finally:
        a2.disconnect()

def client_billed_test_function() -> None:
    """A sample test function. Test with data3"""
    a2 = Assignment2()
    try:
        # TODO: Change this to connect to your own database:
        connected = a2.connect("csc343h-tungcarm", "tungcarm", "")
        print(f"[Connected] Expected True | Got {connected}.")

        # TODO: Test one or more methods here, or better yet, make more testing
        #   functions, with each testing a different aspect of the code.

        # ------------------- Testing Clocked In -----------------------------#

        # These tests assume that you have already loaded the sample data we
        # provided into your database.
        nw = GeoLoc(-5, 60)
        se = GeoLoc(10, 20)
        client_list = a2.clients_within_bounds(nw, se)
        a2.client_billed_totals(client_list)
       
    finally:
        a2.disconnect()

def valid_drivers_test_function() -> None:
    """A sample test function. Test with data4"""
    a2 = Assignment2()
    try:
        # TODO: Change this to connect to your own database:
        connected = a2.connect("csc343h-tungcarm", "tungcarm", "")
        print(f"[Connected] Expected True | Got {connected}.")

        # TODO: Test one or more methods here, or better yet, make more testing
        #   functions, with each testing a different aspect of the code.

        # ------------------- Testing Clocked In -----------------------------#

        # These tests assume that you have already loaded the sample data we
        # provided into your database.
        nw = GeoLoc(-5, 60)
        se = GeoLoc(10, 20)
        a2.valid_drivers(nw, se)
       
    finally:
        a2.disconnect()

def dispatch_test_function() -> None:
    """A sample test function. Test with data4"""
    a2 = Assignment2()
    try:
        # TODO: Change this to connect to your own database:
        connected = a2.connect("csc343h-tungcarm", "tungcarm", "")
        print(f"[Connected] Expected True | Got {connected}.")

        # TODO: Test one or more methods here, or better yet, make more testing
        #   functions, with each testing a different aspect of the code.

        # ------------------- Testing Clocked In -----------------------------#

        # These tests assume that you have already loaded the sample data we
        # provided into your database.
        nw = GeoLoc(-5, 60)
        se = GeoLoc(10, 20)
        a2.dispatch(nw, se, datetime.now())
       
    finally:
        a2.disconnect()


# if __name__ == "__main__":
    # Un comment-out the next two lines if you would like all the doctest
    # examples (see ">>>" in the method and class docstrings) to be run
    # and checked.
    # import doctest
    # doctest.testmod()

    # TODO: Put your testing code here, or call testing functions such as
    #   this one:

    #=== Test this with DATA.SQL===
    # clockin_test_function()

    #=== Test this with DATA1.SQL===
    # pickup_test_function()

    #=== Test this with DATA2.sql===
    # client_within_bounds_test_function()

    #=== Test this with DATA3.sql===
    # client_billed_test_function()

    #=== Test this with data4.sql===
    # valid_drivers_test_function()
    # dispatch_test_function()
    

    
