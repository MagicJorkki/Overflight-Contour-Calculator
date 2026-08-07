# Overflight Contour Calculator

## General

This is a QGIS plugin used to transform raw aircraft track data into easily understandable and visually pleasing polygon shapes (see section "Example of output). The outcome illustrates aircraft traffic and its frequency in a set environment, for example, around an airport.

The calculation methods and the tool’s default settings are based on and in compliance with the UK Civil Aviation Authority's publication [“Definition of overflight” (CAP 1498)](https://www.caa.co.uk/data-and-publications/publications/documents/content/cap1498/), which quite comprehensively describes the process of turning track data into contours. Some details, however, such as whether an observer is always considered to be located at ground level or at a set altitude above mean sea level (MSL), and the interpolation process from calculated points to contour polygons, are not thoroughly defined. Therefore, the user must be aware of exactly what they want to calculate. The user is fully responsible for the calculations and the further use of the tool’s output.

<img width="1600" height="952" alt="image" src="https://github.com/user-attachments/assets/3576902a-c75e-43dc-934b-2ae663bcb884" />


## Simplified Calculation Logic

The calculation is carried out as follows:
1. A grid of points is calculated inside the set extent.
2. For each point, the number of overflights that occurred is calculated using the Definition of Overflight.
3. A polygon layer (or multiple polygon layers) are interpolated using the overflight count values from the point layer.


## Noise vs. Traffic

The output geometries of this tool are visually similar to noise contours often calculated for airports. However, **this tool should not be used to calculate or estimate aircraft noise**, as noise and traffic frequency are fundamentally different concepts.


## Altitude Measures

To understand the decisions made in developing this tool, it is important to understand that the “Definition of Overflight” (CAP 1498) document uses two different measures for altitude: **AGL** (Above Ground Level) and **AMSL** (Above Mean Sea Level). AGL measures an object’s (in this case an aircraft’s) vertical distance to the underlying terrain. AMSL measures the object’s vertical distance to the Vertical Datum, or more commonly, Mean Sea Level (MSL), regardless of the height of the terrain it is currently over.

Were the calculations demonstrated in the document used to support decision-making regarding, for example, air navigation and flight levels, the use of a hard 7,000 ft AMSL ceiling would be justified to keep the outcome in line with other standardized regulatory practices. However, for more social sciences-leaning questions, such as those regarding the experience of the number overflights on a neighbourhood level, an altitude ceiling of 7,000 ft **AGL** (instead of **AMSL**) would be more justifiable. By using AGL instead of AMSL, the physical elevation of the analyzed environment, such as an airport and the surrounding area, won’t affect the calculated outcome.

<img width="1032" height="633" alt="image" src="https://github.com/user-attachments/assets/faea08df-6bd8-45f4-97cf-c2881a2449c4" />


## Observer Point Placement

The “Definition of Overflight” (CAP 1498) document does not specify if the observer points are placed at a constant altitude independent of the local terrain, or if the altitude is derived from a digital elevation model (DEM). By default, this tool assumes a DEM is used, but the user of this tool can instead use a set altitude by selecting “Override DEM With Set Observer Altitude” in the tool menu.

The document also does not specify the grid size (the latitudinal and longitudinal spacing between points). This tool uses a default grid size of 100 m. The user can change this by modifying the value “Grid Size” in the tool menu. It should be noted that a small grid size is likely to cause the calculation to take much longer, while a large grid size negatively affects the quality of the outcome.


## Calculation Extent

Before calculation, the user should define the extent (the area inside which the calculation will be performed). It is recommended to derive the extent from the aircraft track layer, or, if a DEM is used, from the DEM layer.


## Example of Output

img
