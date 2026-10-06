# Texture credits

Surface maps for the 3D Solar System view (equirectangular, 2:1; rings are 1-pixel radial strips from the inner
to the outer edge). Replace any file with a higher-resolution map of the same name; no code changes are needed.

| Files | Source | Licence |
|---|---|---|
| mercury, mars, moon, *_normal, venus_clouds, europa, callisto, ceres, vesta, mimas, enceladus, tethys, dione, rhea, iapetus, saturn_ring, uranus_ring, jupiter_ring, neptune_ring | [Celestia Content](https://github.com/CelestiaProject/CelestiaContent) (`textures/`), built from NASA/JPL, USGS, Björn Jónsson, Paul Schenk, Steve Albers and others (see its README) | GPL-2.0-or-later (Celestia Content default) |
| jupiter (Askaniy Anpilogov; Hubble OPAL + Juno), saturn (Askaniy Anpilogov; NASA/JPL/Björn Jónsson), ganymede (Askaniy Anpilogov; NASA/JPL/USGS, Björn Jónsson, Brian Swift), titan (haze map: Gordan Ugarković, Kevin M. Gill, AstroChara), triton (Askaniy Anpilogov; NASA/JPL/USGS), neptune (Askaniy Anpilogov; NASA/JPL/Björn Jónsson, Karkoschka), phobos (Askaniy Anpilogov; Phil Stooke / NASA PDS), io (ItzImcool, AstroChara; NASA/JPL/USGS, Juno) | Celestia Content | CC BY 3.0 (io: CC BY 4.0, titan: CC BY 4.0) |
| ariel, miranda, titania, oberon, umbriel | Celestia Content (ItzImcool; Paul Schenk; NASA/JPL/Ted Stryk) | CC BY-SA 4.0 |
| deimos | Phil Stooke, Small Bodies Maps v3.0, NASA PDS (via Celestia Content) | CC0 1.0 |
| asteroid, icy | Celestia Content (cubicApocalypse), generic surfaces for bodies without a map | CC BY 4.0 |
| charon | NASA 3D Resources ([github.com/nasa/NASA-3D-Resources](https://github.com/nasa/NASA-3D-Resources)) | Public domain (NASA) |
| earth_day, earth_night, earth_clouds, earth_water | NASA Blue Marble / Black Marble derived maps, via the `three-globe` npm package examples | MIT (package); NASA imagery public domain |
| sun, pluto, uranus | github.com/WaelYasmina/solarsystem | unverified — replace before a commercial release |

The night sky is not a texture: it is drawn from the real HYG star catalogue (CC BY-SA 4.0) and the engine's
Milky Way model. Before a commercial release, check each licence's attribution/share-alike terms.

## Photographs of nebulae and star clusters (`frontend/assets/dso/`)

56 images taken from the Stellarium nebula texture set (github.com/Stellarium/stellarium, `nebulae/default`), keeping
only openly licensed observatory images: NASA/ESA Hubble (public domain / CC BY 4.0), ESO (CC BY 4.0), NOIRLab/KPNO/CTIO
(CC BY 4.0), SDSS, 2MASS and Pan-STARRS1 (free with acknowledgement). Several were cleaned up by Sun Shuwei for
Stellarium. Each image's own credit is in `app/data/space/dso_images.json` and is shown under it in the app.
Rebuild with `python scripts/build_dso_images.py`.

## Drawn pictures

Galaxies, nebulae without a free photograph, star close-ups and star glints are drawn in the browser
(`frontend/js/space/spaceart.js`) from each object's catalogue data (Hubble type, nebula type, temperature, radius).
They are illustrations and are labelled as such.
