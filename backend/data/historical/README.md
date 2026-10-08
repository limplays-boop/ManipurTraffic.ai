# Historical accident source data

These files contain only values transcribed from Ministry of Road Transport and
Highways (MoRTH) publications. They are kept separate by geographic scope and
time period; state totals must not be treated as road-level observations.

## Files

- `morth_manipur_state_accidents_2019_2023.csv` contains Manipur's annual
  accident and fatality counts from *Road Accidents in India 2023*, Tables 5.3
  and 5.8. These are state-wide annual aggregates.
- `morth_manipur_nh_blackspots_2016_2018.csv` contains five Manipur rows from
  Annexure 52 of *Road Accidents in India 2019*. The source reports road names,
  districts, chainage text, and annual accident/fatality counts for 2016–2018.
  Chainage text is preserved as published. Coordinates are blank because the
  report does not provide coordinates and they have not been independently
  verified. The CSV flags a mismatch between the reported and recomputed
  accident total for source row 145 (10 reported; 11 from the yearly counts).
- `user_provided_2024_manipur_state_road_accidents.csv` and
  `user_provided_2024_manipur_state_fatalities.csv` each contain the Manipur
  state row filtered from the user-provided 2024 state summary CSVs. The 2020–2023
  values match the existing MoRTH state totals above. The supplied files did not
  include publication metadata, so verify their source before citing the 2024
  values as authoritative. These are statewide annual aggregates, not crash
  event records.

## Public incident examples for the demo

manipur_public_demo_incidents.csv contains two anonymized example records
summarized from public Manipur Police FIR copies. It keeps the reported time,
location text, vehicle types, and injury outcome while excluding names, phone
numbers, addresses, and vehicle registration numbers. The reports do not supply
verified coordinates, weather, traffic exposure, or matched non-crash
observations. One record is a complainant narrative; neither record is
sufficient to train or validate an accident-risk model. Source URLs are retained
in the CSV for provenance, but the demo API does not return them because the
public FIR copies contain personal details.

## Limits for prediction

These are useful historical context and hotspot records, not a training set for
an accident-probability model. They do not provide individual incident
timestamps, verified coordinates, traffic exposure, matched non-accident
periods, or weather/road conditions for each observation. The five NH rows are
only the Manipur entries present in the report's top-black-spot table; they are
not a complete Manipur crash register. Do not map them as precise points or
combine them with current TomTom/Open-Meteo readings as if those readings were
historical conditions.

For a calibrated model, obtain an authorized event-level export from e-DAR/iRAD
or the relevant Manipur Police/Transport authority, then join it to historical
weather and road/traffic exposure records. The e-DAR portal is at
<https://irad.parivahan.gov.in/>; its data access is role-controlled.

## Sources

- MoRTH, *Road Accidents in India 2023*:
  <https://www.morth.gov.in/sites/default/files/Road-Accident-in-India-2023-Publications.pdf>
- MoRTH, *Road Accidents in India 2019*, Annexure 52:
  <https://morth.gov.in/sites/default/files/RA_Uploading.pdf>
- MoRTH Black Spot MIS summary:
  <https://www.blackspot.morth.gov.in/>
- e-DAR India:
  <https://irad.parivahan.gov.in/>
