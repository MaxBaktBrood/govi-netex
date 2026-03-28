# GOVI Netex
Grenzeloze openbaar vervoer informatie (GOVI) vanuit Netex. Dit script verwerkt Netex-bestanden tot een uitgebreid gpkg-bestand.

This script aims to provide borderless public transport information (GOVI in Dutch) form Netex-files. This script processes Netex-files and saves one detailed gpkg-file.

## Supported/tested datasets
This script supports reading from .zip- and .gz-files, provided in the `./input`-directory. Also, this script has built-in funcitonality to automatically retrieve Netex-datasets. This script aims to treat enum- and epiap-files as general data for the "real" datasets, as it is supposed to. Here's a table indicating the support for these features per dataset:

|Country   |Dataset    |Compatible|Autocollect   |Description                |
|----------|-----------|-----------|--------------|------------------------------------
|[Slovenia](https://nap.si/en/datasets)|All|Not tested|Yes, API|Credentials required
|[Netherlands](https://data.ndovloket.nl/netex)|All|Yes (ENUM, EPIAP)|Yes, SFTP|Credentials required. There is no data for national trains (HRN).

## Part of the revival of GOVI
This project is part of a bigger one. Over 15 years ago, autorities in The Netherlands founded the GOVI-organisation to ensure public transport information was distributed without limits. Today, an extensive load of public transport data is easily accessible, but the data is often limited to a specific country. To be truely limitless, public transport data should not be viewed per country.

GOVI changed it's name to DOVA. DOVA became focussed on domestic developments, while challenging the limitlessness of public transport is still important. This is why, as of april 2026, GOVI returns. This time, borderless information will be the sole goal of GOVI!