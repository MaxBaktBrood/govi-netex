# GOVI Netex
Grenzeloze openbaar vervoer informatie (GOVI) vanuit Netex. Dit script verwerkt Netex-bestanden tot een uitgebreid gpkg-bestand.

This script aims to provide borderless public transport information (GOVI in Dutch) from Netex-files. This script processes Netex-files and saves one detailed gpkg-file.

## Supported/tested datasets
This script supports reading from .zip- and .gz-files, provided in the `./input`-directory. Also, this script has built-in functionality to automatically retrieve Netex-datasets. This script aims to treat enum- and epiap-files as general data for the "real" datasets, as it is supposed to. Here's a table indicating the support for these features per dataset:

|Country   |Dataset    |Compatible|Autocollect   |Description                |
|----------|-----------|-----------|--------------|------------------------------------
|[Slovenia](https://nap.si/en/datasets)|All|Not tested|Yes, API|Credentials required
|[Netherlands](https://data.ndovloket.nl/netex)|All|Yes (ENUM, EPIAP)|Yes, SFTP|Credentials required. There is no data for most trains.
|[Luxembourg](https://data.public.lu/en/datasets/horaires-et-arrets-des-transport-publics-netex/)|All|No|No|No route data.
|[France](https://transport.data.gouv.fr/datasets?format=NeTEx)|Réseau SNCF TGV, Intercités et TER|Mostly|No|Geodata is point-to-point.
|[Norway](https://developer.entur.org/stops-and-timetable-data)|All|No|Yes, link|
|[Belgium](https://data.belgianmobility.io/nl/data.html#)|All|Not tested|No|
|[Austria](https://data.mobilitaetsverbuende.at/en/data-sets)|All|Not tested|No|
|[Germany](https://www.opendata-oepnv.de/ht/de/datensaetze)|All|Not tested|No|No route data.
|[Finland](https://mobility.mobility-database.fintraffic.fi/en)|All|No|Yes, link|
|[United Kingdom](https://data.bus-data.dft.gov.uk/)|All|No|No|Timetables aren't NeTEx
|[Italy](https://www.cciss.it/nap/mmtis/public/en/catalog/Asset)|All|Not tested|No|
|[Switzerland](https://data.opentransportdata.swiss/organization/oevch?q=netex&sort=score+desc%2C+metadata_modified+desc)|All|No|No|No route data.
|[Sweden](https://www.trafiklab.se/api/netex-datasets/netex-sweden/)|All|No|Yes, link|Api key required.

## Part of the revival of GOVI
This project is part of a bigger one. Over 15 years ago, authorities in The Netherlands founded the GOVI-organisation to ensure public transport information was distributed without limits. Today, an extensive load of public transport data is easily accessible, but the data is often limited to a specific country. To be truly limitless, public transport data should not be viewed per country.

GOVI changed it's name to DOVA. DOVA became focussed on domestic developments, while challenging the limitlessness of public transport is still important. This is why, as of April 2026, GOVI returns. This time, borderless information will be the sole goal of GOVI!