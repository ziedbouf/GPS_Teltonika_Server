CREATE TABLE public.gps_data
(
    imei numeric NOT NULL,
    "timestamp" numeric NOT NULL,
    latitude numeric,
    longitude numeric,
    altitude numeric,
    course numeric(3,0),
    satellites numeric(2,0),
    speed numeric,
    ioevents json
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.gps_data
    OWNER to gps_teltonika;

CREATE INDEX imei_idx
    ON public.gps_data USING btree
    (imei DESC NULLS LAST)
    TABLESPACE pg_default;

CREATE INDEX lat_idx
    ON public.gps_data USING btree
    (latitude ASC NULLS LAST)
    TABLESPACE pg_default;

CREATE INDEX lng_idx
    ON public.gps_data USING btree
    (longitude ASC NULLS LAST)
    TABLESPACE pg_default;

CREATE INDEX timestamp_idx
    ON public.gps_data USING btree
    ("timestamp" DESC NULLS LAST)
    TABLESPACE pg_default;