from dataclasses import dataclass, fields, astuple, asdict
import typing
from typing import Optional
from datetime import datetime

@dataclass
class Branding:
    id: str
    name: Optional[str] = None
    url: Optional[str] = None

@dataclass
class ProductType:
    id: str
    name: Optional[str] = None

@dataclass
class Operator:
    id: str
    name: Optional[str] = None
    code: Optional[str] = None        
    
@dataclass
class Authority:
    id: str
    name: Optional[str] = None
    code: Optional[str] = None  

@dataclass
class Area:
    id: str
    name: Optional[str] = None
    code: Optional[str] = None

@dataclass
class RelResponsibilityArea:
    id: str
    responsibility: str
    area_ref: Optional[str] = None

@dataclass
class Line:
    id: str
    code: Optional[str] = None
    branding: Optional[str] = None
    name: Optional[str] = None
    number: Optional[str] = None
    transport_mode: Optional[str] = None
    transport_sub_mode: Optional[str] = None
    public_code: Optional[str] = None
    authority: Optional[str] = None
    operator: Optional[str] = None
    type_of_product: Optional[str] = None
    type_of_service: Optional[str] = None
    responsibility_set: Optional[str] = None
    custom_category: Optional[str] = None

@dataclass
class Route:
    id: str
    line: Optional[str] = None
    direction: Optional[str] = None

@dataclass
class RelPointRoute:
    route: str
    point_order: int
    point: str
    link: Optional[str] = None

@dataclass
class Routepoint:
    id: str
    location: Optional[str] = None

@dataclass
class Routelink:
    id: str
    location: Optional[str] = None

@dataclass
class Runtime:
    id: str
    time_demand_type: str
    timing_link: Optional[str] = None
    time: Optional[float] = None

@dataclass 
class Waittime:
    id: str
    time_demand_type: str
    scheduled_stop_point: Optional[str] = None
    timing_point: Optional[str] = None
    time: Optional[float] = None

@dataclass
class TimingLink:
    id: str
    distance: float = 0.0

@dataclass
class RelTimingRoutePoint:
    id: str
    routepoint: str = None

@dataclass
class Pattern:
    id: str
    route: Optional[str] = None
    direction: Optional[str] = None

@dataclass
class PointInPattern:
    id: str
    pattern: str
    point_order: Optional[int] = None
    timing_point: Optional[str] = None
    stoppoint: Optional[str] = None
    timing_link: Optional[str] = None

@dataclass
class ScheduledStopPoint:
    id: str
    route_point: Optional[str] = None
    name: Optional[str] = None
    stop_area: Optional[str] = None
    location: Optional[str] = None

@dataclass
class StopArea:
    id: str
    public_code: Optional[str] = None
    private_code: Optional[str] = None
    name: Optional[str] = None
    place_name: Optional[str] = None

@dataclass
class AvailabilityCondition:
    id: str
    available_from: Optional[datetime] = None
    available_through: Optional[datetime] = None
    bits: Optional[str] = None

@dataclass
class Journey:
    id: str
    number: Optional[str] = None
    pattern: Optional[str] = None
    in_scope_of_operator: Optional[bool] = None
    realtime_info: Optional[bool] = None
    vehicle_type: Optional[str] = None
    starting_time: Optional[str] = None
    time_demand_type: Optional[str] = None

@dataclass
class AvailabilityPerJourney:
    journey: str
    availability: str

@dataclass 
class RelStoppointQuaycode:
    id: Optional[str] = None
    quay: Optional[str] = None

@dataclass
class RelQuayStopplace:
    stopplace: str
    quay: str
    
@dataclass
class Stopplace:
    id: str
    name: Optional[str] = None
    location: Optional[str] = None

@dataclass
class Notice:
    id: str
    notice_for: str
    text: str