from enum import Enum


class StatusInfo(Enum):
    # OGC Processes 7.12.2 | statusInfo Enum | https://docs.ogc.org/is/18-062r2/18-062r2.html#toc33
    FAILURE = "failed"
    PENDING = "running"
    SUCCESS = "successful"
    ACCEPTED = "accepted"