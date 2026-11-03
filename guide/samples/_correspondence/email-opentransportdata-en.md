**To:** opentransportdata.swiss (contact address or form on opentransportdata.swiss)

**Subject:** Using a dated snapshot of the Service Points (Didok) data in open-source documentation

Dear opentransportdata.swiss team,

I develop refiroo, an open-source application for managing reference data (licence: AGPL-3.0). We are
writing its user guide and would like to use part of the Service Points (Didok) dataset as the guide's
running example, because it is a clear, real case of codes, validity dates and multilingual names.

What we plan to use:
- The service points of the canton of Graubünden: about 2,400 records with UIC number, SLOID,
  designation, abbreviation, validity period, canton, district and municipality, means of transport and
  operator.
- A snapshot dated 2 November 2026, read through the data.sbb.ch API.

How we plan to use it:
- As example data in the guide, which is published as a public website and served by the application
  itself.
- As sample files in our public source repository, and loaded into a demonstration instance that people
  can start with Docker.
- Each copy is labelled "Source: opentransportdata.swiss, Service Points (Didok), Federal Office of
  Transport / SBB, snapshot 2026-11-02", with a link to the dataset.
- The repository also contains a script that downloads the current data, so users can replace the
  snapshot with up-to-date records.

Our question concerns the requirement in your terms of use that data be updated at the same frequency
as the raw data. Does this requirement apply to a clearly dated snapshot used only as example data in
documentation? If it does, would a dated snapshot plus the refresh script meet it? We would also be
grateful to know whether our attribution text is correct, and whether anything else is required.

The project: [repository link]

Thank you for publishing this data, and for your help.

Kind regards,
Krisztian Toth
