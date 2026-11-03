---
title: The example data
description: Meet the public transport reference data used in the guide's screenshots and its sources.
reader: evaluator
---

This guide uses the public transport stops of Graubünden, Switzerland, to show refiroo with
recognisable records and connections. The reference instance's Graubünden workspace runs the
model Public transport stops of Graubünden 1.0.0. Its data is a dated snapshot from **2 November
2026**, rather than a current transport information service.

The model defines three applications, Network, Systems and Names. They demonstrate capabilities;
refiroo does not require these applications or know what their record types mean.

## Network

Network holds stops, cantons, districts, municipalities, operators and transport modes. The
Stops table demonstrates [records](/docs/use/records/),
[lists and filters](/docs/use/lists-and-filters/) and
[finding records](/docs/guide/use/find-records/).
Geography arranges canton, district, municipality and stop; Modes nests modes under other modes.
Both demonstrate [hierarchies](/docs/use/hierarchies/). [Relationships](/docs/use/relationships/) connect stops to operators
and modes without making those records their parents.

![The Network application showing stops with numbers, dates and operators](/docs/screens/app-network.png)

*Above: Network in Graubünden shows the Stops collection. The reference set contains 2,443 stops,
100 municipalities and 71 operators. The numbers describe this snapshot, not refiroo's limits.*

## Systems

Systems holds records for other systems and their codes. Its System codes
[hierarchy](/docs/use/hierarchies/) organises codes beneath systems and groups. [Mapping grids](/docs/use/mapping-grids/)
connect those codes to stops or municipalities. A [relation matrix](/docs/use/relation-matrices/)
compares municipalities against systems to show where codes exist.

![A mapping grid with fictional codes demonstrating three mapping states](/docs/screens/mapping-grid-codes-to-stops.png)

*Above: Codes to stops is searched for FICTIONAL. Regional ticketing (FICTIONAL) and every T-code
shown are invented. T-0300 connects to both Chur West and Chur to demonstrate ambiguity; T-9999
is deliberately unmapped. Other codes demonstrate a single mapping.*

The fictional ticketing data uses real stop names and numbers so the connection can be inspected.
It does not describe a real ticketing service or fare entitlement. Wikidata codes in the reference
data are real item identifiers.

## Names

Names holds languages and name translations related to municipalities and operators. Its [relation matrices](/docs/use/relation-matrices/)
compare those records across English, French, German, Italian and Romansh. It is the same idea
as the starter model's RDM Translations: records, an owning relationship and matrices, configured
for different types. See [Translations as an example](/docs/examples/translations/).

![The Names application showing municipalities and their names across five languages](/docs/screens/app-names.png)

*Above: Municipality names compares related name records by language. Active is Yes determines
which records count in a cell under this model's rule.*

The guide also shows a missing Romansh name for Bonaduz. That name was removed for the captures,
then the name Panaduz was recreated. Those screenshots demonstrate creation; they are not a claim
that the name is still missing from the reference set. Other illustrated relationship and move dialogs were
cancelled. For the working steps, see
[Fill in a relation matrix](/docs/guide/use/fill-in-a-relation-matrix/).

## Working with the example

These applications share the same [change sets](/docs/use/change-sets/),
[publications](/docs/use/publications/) and [history](/docs/use/history/) as any other
model. What you can read or change depends on your [roles and grants](/docs/administer/roles-and-grants/).
The model also declares a read-only contract for other systems; see
[The consumer API example](/docs/examples/the-consumer-api/#the-populated-reference-example).

## Sources and attribution

Stops, operators, means of transport, and the canton, district and municipality names and numbers
come from the Didok service-point data, read through the SBB open-data service. Multilingual
municipality and canton names and municipality and station item identifiers come from Wikidata.
The reference set combines those sources with the clearly labelled fictional ticketing system.

**Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB,
snapshot 2026-11-02. Wikidata, CC0.**

These are sample records for learning the controls. Check current authoritative data before
using names, codes or dates for operational decisions. The separate Default workspace in the
screenshots shows the [starter model](/docs/examples/the-starter-model/) without data.
