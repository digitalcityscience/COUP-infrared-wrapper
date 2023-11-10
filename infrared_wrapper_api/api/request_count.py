import datetime
import pytz

from infrared_wrapper_api.utils import get_request_log_count

# RUN AS CHRON
if __name__ == "__main__":

    tz = pytz.timezone('Europe/Berlin')
    berlin_now = datetime.datetime.now(tz)

    for sim_type in ["wind", "sun"]:
        count = get_request_log_count(sim_type)
        print(f"{count} {sim_type} simulations counted until {berlin_now}")
