"""Real launch vehicles, their stages and real satellites, from public figures (agency fact sheets, press kits
and standard references). Stage modules combine tank + engines; strap-on boosters fly beside the core stage.

Numbers are rounded and some are derived (for example thrust from propellant, burn time and Isp), so treat
them as good approximations rather than official data. Masses in kg, thrust in N, Isp in s, sizes in m."""


def stage(name, agency, dry, prop, thrust_sl, thrust_vac, isp_sl, isp_vac, height, width, **extra):
    return {"name": name, "agency": agency, "category": "stage", "mass": dry, "prop": prop, "thrust_sl": thrust_sl,
            "thrust_vac": thrust_vac, "isp_sl": isp_sl, "isp_vac": isp_vac, "height": height, "width": width,
            "shrouded": True, **extra}


def booster(name, agency, dry, prop, thrust_sl, thrust_vac, isp_sl, isp_vac, height, width, solid):
    return {"name": name, "agency": agency, "category": "booster", "mass": dry, "prop": prop, "thrust_sl": thrust_sl,
            "thrust_vac": thrust_vac, "isp_sl": isp_sl, "isp_vac": isp_vac, "height": height, "width": width, "solid": solid}


VEHICLE_PARTS: dict[str, dict] = {
    # --- ISRO
    "pslv_psom_xl": booster("PSOM-XL strap-on (solid)", "ISRO", 2_800, 12_200, 425e3, 440e3, 253, 262, 13.5, 1.0, True),
    "pslv_ps1": stage("PSLV PS1 (S139 solid)", "ISRO", 30_200, 138_000, 2_917e3, 3_311e3, 237, 269, 20.0, 2.8, solid=True),
    "pslv_ps2": stage("PSLV PS2 (Vikas)", "ISRO", 5_300, 42_000, 700e3, 799e3, 257, 293, 12.8, 2.8),
    "pslv_ps3": stage("PSLV PS3 (HPS3 solid)", "ISRO", 1_100, 7_600, 180e3, 240e3, 221, 295, 3.6, 2.0, solid=True),
    "pslv_ps4": stage("PSLV PS4 (twin L2.5)", "ISRO", 920, 2_500, 6e3, 15.2e3, 122, 308, 3.0, 2.8),
    "gslv_l40": booster("L40 strap-on (Vikas)", "ISRO", 5_600, 42_700, 732e3, 819e3, 262, 293, 19.7, 2.1, False),
    "gslv_gs1": stage("GSLV GS1 (S139 solid)", "ISRO", 28_300, 138_200, 2_917e3, 3_311e3, 237, 269, 20.1, 2.8, solid=True),
    "gslv_gs2": stage("GSLV GS2 (high-thrust Vikas)", "ISRO", 5_100, 39_500, 700e3, 846e3, 244, 295, 11.6, 2.8),
    "gslv_cus": stage("GSLV CUS (CE-7.5 cryogenic)", "ISRO", 3_000, 15_000, 30e3, 75e3, 180, 454, 8.7, 2.8),
    "lvm3_s200": booster("S200 strap-on (solid)", "ISRO", 31_000, 205_000, 3_566e3, 4_312e3, 227, 274.5, 26.2, 3.2, True),
    "lvm3_l110": stage("LVM3 L110 (twin Vikas)", "ISRO", 9_800, 116_000, 1_370e3, 1_598e3, 251, 293, 21.4, 4.0),
    "lvm3_c25": stage("LVM3 C25 (CE-20 cryogenic)", "ISRO", 5_300, 28_000, 80e3, 200e3, 177, 443, 13.5, 4.0),
    "sslv_ss1": stage("SSLV SS1 (solid)", "ISRO", 9_500, 87_000, 2_178e3, 2_378e3, 240, 262, 20.0, 2.0, solid=True),
    "sslv_ss2": stage("SSLV SS2 (solid)", "ISRO", 1_300, 7_700, 150e3, 184e3, 225, 276, 4.7, 2.0, solid=True),
    "sslv_ss3": stage("SSLV SS3 (solid)", "ISRO", 900, 4_500, 90e3, 120e3, 217, 290, 3.2, 1.7, solid=True),
    # --- SpaceX
    "f9_s1": stage("Falcon 9 first stage (9 Merlin 1D)", "SpaceX", 25_600, 411_000, 7_607e3, 8_227e3, 282, 311, 41.2, 3.7),
    "f9_s2": stage("Falcon 9 second stage (Merlin Vacuum)", "SpaceX", 4_000, 107_500, 420e3, 981e3, 150, 348, 13.8, 3.7),
    "fh_side": booster("Falcon Heavy side booster", "SpaceX", 22_200, 411_000, 7_607e3, 8_227e3, 282, 311, 41.2, 3.7, False),
    "sh_booster": stage("Super Heavy (33 Raptor)", "SpaceX", 200_000, 3_400_000, 74_400e3, 79_000e3, 327, 347, 71.0, 9.0),
    "starship": stage("Starship upper stage (6 Raptor)", "SpaceX", 100_000, 1_200_000, 6_000e3, 14_700e3, 300, 370, 50.0, 9.0),
    # --- NASA
    "sv_sic": stage("Saturn V S-IC (5 F-1)", "NASA", 131_000, 2_160_000, 34_020e3, 38_700e3, 263, 304, 42.0, 10.1),
    "sv_sii": stage("Saturn V S-II (5 J-2)", "NASA", 36_000, 444_000, 3_800e3, 5_115e3, 200, 421, 24.9, 10.1),
    "sv_sivb": stage("Saturn V S-IVB (J-2)", "NASA", 12_000, 109_000, 400e3, 1_033e3, 200, 421, 17.8, 6.6),
    "sls_srb": booster("SLS five-segment booster (solid)", "NASA", 98_000, 631_000, 11_885e3, 13_211e3, 242, 269, 54.0, 3.7, True),
    "sls_core": stage("SLS core stage (4 RS-25)", "NASA", 85_000, 987_000, 7_440e3, 9_116e3, 366, 452, 64.6, 8.4),
    "sls_icps": stage("SLS ICPS (RL10B-2)", "NASA", 3_500, 27_200, 40e3, 110e3, 200, 462, 13.7, 5.1),
    # --- ESA / Arianespace
    "a5_eap": booster("Ariane 5 EAP booster (solid)", "ESA", 33_000, 240_000, 4_526e3, 4_979e3, 250, 275, 31.6, 3.05, True),
    "a5_epc": stage("Ariane 5 EPC core (Vulcain 2)", "ESA", 14_700, 175_000, 960e3, 1_390e3, 310, 432, 30.5, 5.4),
    "a5_esca": stage("Ariane 5 ESC-A (HM7B)", "ESA", 4_540, 14_900, 20e3, 67e3, 150, 446, 4.7, 5.4),
    # --- Roscosmos
    "soyuz_bvgd": booster("Soyuz strap-on block (RD-107A)", "Roscosmos", 3_800, 39_600, 839e3, 1_020e3, 263, 320, 19.6, 2.7, False),
    "soyuz_a": stage("Soyuz core Block A (RD-108A)", "Roscosmos", 6_550, 90_100, 792e3, 990e3, 255, 319, 27.1, 2.95),
    "soyuz_i": stage("Soyuz-2.1b Block I (RD-0124)", "Roscosmos", 2_410, 25_300, 120e3, 294e3, 200, 359, 6.7, 2.66),
    # --- CNSA
    "cz5_booster": booster("Long March 5 booster (2 YF-100)", "CNSA", 12_000, 135_000, 2_400e3, 2_680e3, 300, 335, 27.6, 3.35, False),
    "cz5_core": stage("Long March 5 core (2 YF-77)", "CNSA", 17_000, 158_000, 1_020e3, 1_400e3, 310, 430, 33.2, 5.0),
    "cz5_upper": stage("Long March 5 upper stage (2 YF-75D)", "CNSA", 3_400, 23_000, 70e3, 176e3, 180, 442, 11.5, 5.0),
    # --- Rocket Lab
    "electron_s1": stage("Electron first stage (9 Rutherford)", "Rocket Lab", 950, 9_250, 192e3, 224e3, 303, 330, 12.1, 1.2),
    "electron_s2": stage("Electron second stage (Rutherford Vacuum)", "Rocket Lab", 250, 2_150, 10e3, 25.8e3, 150, 343, 2.4, 1.2),
    # --- spacecraft and fairings of those vehicles
    "apollo_csm": {"name": "Apollo command & service module", "agency": "NASA", "category": "command", "mass": 11_900, "prop": 18_400,
                   "thrust_sl": 40e3, "thrust_vac": 91e3, "isp_sl": 150, "isp_vac": 314, "height": 11.0, "width": 3.9, "crew": 3,
                   "shrouded": True},
    "apollo_lm": {"name": "Apollo lunar module (carried)", "agency": "NASA", "category": "satellite", "mass": 15_100, "height": 7.0, "width": 4.3},
    "orion": {"name": "Orion + European Service Module", "agency": "NASA / ESA", "category": "command", "mass": 16_000, "prop": 8_600,
              "thrust_sl": 12e3, "thrust_vac": 26.7e3, "isp_sl": 150, "isp_vac": 316, "height": 8.0, "width": 5.2, "crew": 4,
              "shrouded": True},
    "soyuz_ms": {"name": "Soyuz MS crew spacecraft", "agency": "Roscosmos", "category": "command", "mass": 7_080, "height": 7.5, "width": 2.7, "crew": 3},
    "fairing_2m": {"name": "Payload fairing 2 m", "category": "aero", "mass": 300, "height": 3.5, "width": 2.1},
    "fairing_3m": {"name": "Payload fairing 3.2 m", "category": "aero", "mass": 1_150, "height": 5.0, "width": 3.2},
    "fairing_4m": {"name": "Payload fairing 4 m", "category": "aero", "mass": 1_800, "height": 5.5, "width": 4.0},
}

# Real satellites. `parts` gives the payload as a rocket part; `fleet` describes it once in orbit (drag area,
# propulsion and instruments) and its usual orbit.
SATELLITES: dict[str, dict] = {
    "cartosat3": {"name": "Cartosat-3", "agency": "ISRO", "mass": 1_625, "height": 3.2, "width": 2.2, "launched": "PSLV-C47, 2019",
                  "purpose": "Very high resolution Earth imaging",
                  "orbit": {"altitude_km": 509, "inclination_deg": 97.5},
                  "fleet": {"area_m2": 9.0, "cd": 2.2, "propellant_kg": 60, "isp": 220, "thrust": 11.0,
                            "camera": {"type": "optical", "aperture_m": 1.2, "ifov_urad": 0.55, "pixels_across": 57_000,
                                       "bands": ["panchromatic", "blue", "green", "red", "near-infrared"], "max_off_nadir_deg": 45}}},
    "eos05": {"name": "EOS-05 (GISAT-1A)", "agency": "ISRO", "mass": 2_367, "height": 3.8, "width": 2.5, "launched": "GSLV-F17, 4 Sep 2026",
              "purpose": "Imaging India every few minutes from geosynchronous orbit",
              "orbit": {"altitude_km": 35_786, "inclination_deg": 0.1, "longitude_deg": 85.0},
              "fleet": {"area_m2": 25.0, "cd": 2.2, "propellant_kg": 1_100, "isp": 315, "thrust": 440.0,
                        "camera": {"type": "optical", "aperture_m": 0.7, "ifov_urad": 1.17, "pixels_across": 10_000,
                                   "bands": ["6-band VNIR multispectral (42 m)", "158-band VNIR hyperspectral (318 m)",
                                             "256-band SWIR hyperspectral (191 m)"], "max_off_nadir_deg": 9}}},
    "eos04": {"name": "EOS-04 (RISAT-1A)", "agency": "ISRO", "mass": 1_710, "height": 3.0, "width": 2.6, "launched": "PSLV-C52, 2022",
              "purpose": "All-weather, day-and-night C-band radar imaging",
              "orbit": {"altitude_km": 529, "inclination_deg": 97.5},
              "fleet": {"area_m2": 14.0, "cd": 2.2, "propellant_kg": 80, "isp": 220, "thrust": 11.0,
                        "camera": {"type": "sar", "band": "C-band 5.35 GHz", "resolution_m": 3.0, "swath_km": 25,
                                   "min_off_nadir_deg": 15, "max_off_nadir_deg": 45}}},
    "landsat9": {"name": "Landsat 9", "agency": "NASA / USGS", "mass": 2_711, "height": 4.3, "width": 3.0, "launched": "Atlas V, 2021",
                 "purpose": "Long-term land imaging (OLI-2 and TIRS-2)",
                 "orbit": {"altitude_km": 705, "inclination_deg": 98.2},
                 "fleet": {"area_m2": 15.0, "cd": 2.2, "propellant_kg": 395, "isp": 220, "thrust": 22.0,
                           "camera": {"type": "optical", "aperture_m": 0.135, "ifov_urad": 21.3, "pixels_across": 6_200,
                                      "bands": ["coastal", "blue", "green", "red", "near-infrared", "SWIR 1", "SWIR 2",
                                                "panchromatic (15 m)", "cirrus"], "max_off_nadir_deg": 7.5}}},
    "sentinel2a": {"name": "Sentinel-2A", "agency": "ESA", "mass": 1_140, "height": 3.4, "width": 1.7, "launched": "Vega, 2015",
                   "purpose": "Copernicus land monitoring (13 bands, 10 m)",
                   "orbit": {"altitude_km": 786, "inclination_deg": 98.6},
                   "fleet": {"area_m2": 9.0, "cd": 2.2, "propellant_kg": 123, "isp": 220, "thrust": 1.0,
                             "camera": {"type": "optical", "aperture_m": 0.15, "ifov_urad": 12.7, "pixels_across": 29_000,
                                        "bands": ["13 bands, 443 to 2190 nm"], "max_off_nadir_deg": 10.3}}},
    "worldview3": {"name": "WorldView-3", "agency": "Maxar", "mass": 2_800, "height": 5.7, "width": 2.5, "launched": "Atlas V, 2014",
                   "purpose": "Commercial 31 cm imaging",
                   "orbit": {"altitude_km": 617, "inclination_deg": 97.97},
                   "fleet": {"area_m2": 12.0, "cd": 2.2, "propellant_kg": 100, "isp": 220, "thrust": 22.0,
                             "camera": {"type": "optical", "aperture_m": 1.1, "ifov_urad": 0.5, "pixels_across": 35_000,
                                        "bands": ["panchromatic (0.31 m)", "8 multispectral (1.24 m)", "8 SWIR (3.7 m)"],
                                        "max_off_nadir_deg": 45}}},
    "insat3ds": {"name": "INSAT-3DS", "agency": "ISRO", "mass": 2_275, "height": 3.6, "width": 2.4, "launched": "GSLV-F14, 2024",
                 "purpose": "Weather imaging and sounding from geostationary orbit",
                 "orbit": {"altitude_km": 35_786, "inclination_deg": 0.1, "longitude_deg": 82.0},
                 "fleet": {"area_m2": 25.0, "cd": 2.2, "propellant_kg": 1_250, "isp": 315, "thrust": 440.0,
                           "camera": {"type": "optical", "aperture_m": 0.31, "ifov_urad": 28.0, "pixels_across": 12_000,
                                      "bands": ["visible (1 km)", "SWIR", "MIR", "water vapour", "thermal IR (4 km)"],
                                      "max_off_nadir_deg": 9}}},
    "starlink_v2mini": {"name": "Starlink V2 Mini", "agency": "SpaceX", "mass": 800, "height": 2.0, "width": 2.7, "launched": "Falcon 9, 2023 on",
                        "purpose": "Broadband internet (argon Hall-effect thrusters)",
                        "orbit": {"altitude_km": 550, "inclination_deg": 53.0},
                        "fleet": {"area_m2": 30.0, "cd": 2.2, "propellant_kg": 40, "isp": 2_500, "thrust": 0.17, "camera": None}},
    "gps3": {"name": "GPS III", "agency": "US Space Force", "mass": 3_880, "height": 2.5, "width": 2.4, "launched": "Falcon 9, 2018 on",
             "purpose": "Navigation", "orbit": {"altitude_km": 20_180, "inclination_deg": 55.0},
             "fleet": {"area_m2": 20.0, "cd": 2.2, "propellant_kg": 300, "isp": 220, "thrust": 22.0, "camera": None}},
    "hubble": {"name": "Hubble Space Telescope", "agency": "NASA / ESA", "mass": 11_110, "height": 13.2, "width": 4.2,
               "launched": "Space Shuttle Discovery, 1990", "purpose": "Astronomy (points away from Earth)",
               "orbit": {"altitude_km": 515, "inclination_deg": 28.5},
               "fleet": {"area_m2": 45.0, "cd": 2.2, "propellant_kg": 0, "isp": 0, "thrust": 0.0, "camera": None}},
}

for _sid, _s in SATELLITES.items():
    VEHICLE_PARTS[f"sat_{_sid}"] = {"name": _s["name"], "agency": _s["agency"], "category": "satellite", "mass": _s["mass"],
                                    "height": _s["height"], "width": _s["width"], "catalog_satellite": _sid}
VEHICLE_PARTS["sat_starlink_batch"] = {"name": "Starlink V2 Mini × 22", "agency": "SpaceX", "category": "satellite",
                                       "mass": 17_600, "height": 6.0, "width": 3.6}


def P(part, count=None):
    return {"part": part, "count": count} if count else {"part": part}


# Vehicles: stack bottom to top, the launch site they usually fly from and published performance
VEHICLES: dict[str, dict] = {
    "pslv_xl": {"name": "PSLV-XL", "agency": "ISRO", "country": "India", "first_flight": 2008, "site": "sriharikota",
                "payload_leo_kg": 3_800, "payload_sso_kg": 1_750,
                "parts": [P("pslv_ps1"), P("pslv_psom_xl", 6), P("decoupler_real_3m"), P("pslv_ps2"), P("decoupler_real_3m"),
                          P("pslv_ps3"), P("decoupler_real_2m"), P("pslv_ps4"), P("decoupler_real_3m"), P("sat_cartosat3"), P("fairing_3m")]},
    "gslv_mk2": {"name": "GSLV Mk II", "agency": "ISRO", "country": "India", "first_flight": 2001, "site": "sriharikota",
                 "payload_leo_kg": 6_000, "payload_gto_kg": 2_500,
                 "parts": [P("gslv_gs1"), P("gslv_l40", 4), P("decoupler_real_3m"), P("gslv_gs2"), P("decoupler_real_3m"), P("gslv_cus"),
                           P("decoupler_real_3m"), P("sat_eos05"), P("fairing_4m")]},
    "lvm3": {"name": "LVM3", "agency": "ISRO", "country": "India", "first_flight": 2017, "site": "sriharikota",
             "payload_leo_kg": 8_000, "payload_gto_kg": 4_000,
             "parts": [P("lvm3_l110"), P("lvm3_s200", 2), P("decoupler_real_4m"), P("lvm3_c25"), P("decoupler_real_4m"),
                       P("sat_lunar"), P("fairing_xl")]},
    "sslv": {"name": "SSLV", "agency": "ISRO", "country": "India", "first_flight": 2022, "site": "sriharikota",
             "payload_leo_kg": 500,
             "parts": [P("sslv_ss1"), P("decoupler_real_2m"), P("sslv_ss2"), P("decoupler_real_2m"), P("sslv_ss3"),
                       P("decoupler_real_2m"), P("sat_cubesat"), P("fairing_2m")]},
    "falcon9": {"name": "Falcon 9 Block 5", "agency": "SpaceX", "country": "USA", "first_flight": 2018, "site": "canaveral",
                "payload_leo_kg": 22_800, "payload_gto_kg": 8_300,
                "parts": [P("f9_s1"), P("decoupler_real_4m"), P("f9_s2"), P("decoupler_real_4m"), P("sat_starlink_batch"), P("fairing_xl")]},
    "falcon_heavy": {"name": "Falcon Heavy", "agency": "SpaceX", "country": "USA", "first_flight": 2018, "site": "canaveral",
                     "payload_leo_kg": 63_800, "payload_gto_kg": 26_700,
                     "parts": [P("f9_s1"), P("fh_side", 2), P("decoupler_real_4m"), P("f9_s2"), P("decoupler_real_4m"), P("sat_gps3"),
                               P("fairing_xl")]},
    "starship": {"name": "Starship (design targets)", "agency": "SpaceX", "country": "USA", "first_flight": 2023, "site": "canaveral",
                 "payload_leo_kg": 150_000,
                 "parts": [P("sh_booster"), P("decoupler_real_9m"), P("starship"), P("sat_starlink_batch"), P("sat_starlink_batch")]},
    "saturn_v": {"name": "Saturn V (Apollo)", "agency": "NASA", "country": "USA", "first_flight": 1967, "site": "canaveral",
                 "payload_leo_kg": 140_000, "payload_tli_kg": 48_600,
                 "parts": [P("sv_sic"), P("decoupler_real_10m"), P("sv_sii"), P("decoupler_real_7m"), P("sv_sivb"), P("decoupler_real_7m"),
                           P("apollo_lm"), P("apollo_csm"), P("nose")]},
    "sls_block1": {"name": "SLS Block 1 (Artemis)", "agency": "NASA", "country": "USA", "first_flight": 2022, "site": "canaveral",
                   "payload_leo_kg": 95_000, "payload_tli_kg": 27_000,
                   "parts": [P("sls_core"), P("sls_srb", 2), P("decoupler_real_5m"), P("sls_icps"), P("decoupler_real_5m"), P("orion"), P("nose")]},
    "ariane5": {"name": "Ariane 5 ECA", "agency": "ESA", "country": "Europe", "first_flight": 2002, "site": "kourou",
                "payload_leo_kg": 21_000, "payload_gto_kg": 10_500,
                "parts": [P("a5_epc"), P("a5_eap", 2), P("decoupler_real_5m"), P("a5_esca"), P("decoupler_real_5m"), P("sat_comms"),
                          P("fairing_xl")]},
    "soyuz21b": {"name": "Soyuz-2.1b", "agency": "Roscosmos", "country": "Russia", "first_flight": 2006, "site": "baikonur",
                 "payload_leo_kg": 8_200,
                 "parts": [P("soyuz_a"), P("soyuz_bvgd", 4), P("decoupler_real_3m"), P("soyuz_i"), P("decoupler_real_3m"), P("soyuz_ms"),
                           P("nose")]},
    "long_march5": {"name": "Long March 5", "agency": "CNSA", "country": "China", "first_flight": 2016, "site": "wenchang",
                    "payload_gto_kg": 14_000,
                    "parts": [P("cz5_core"), P("cz5_booster", 4), P("decoupler_real_5m"), P("cz5_upper"), P("decoupler_real_5m"),
                              P("sat_telescope"), P("fairing_xl")]},
    "electron": {"name": "Electron", "agency": "Rocket Lab", "country": "USA / New Zealand", "first_flight": 2017, "site": "mahia",
                 "payload_leo_kg": 300,
                 "parts": [P("electron_s1"), P("decoupler_real_1m"), P("electron_s2"), P("decoupler_real_1m"), P("sat_cubesat"),
                           P("fairing_s")]},
}

# Decouplers of real vehicles: their mass is part of the stage masses, so they weigh nothing extra
for _w, _tag in ((1.2, "1m"), (2.0, "2m"), (2.8, "3m"), (4.0, "4m"), (5.2, "5m"), (6.6, "7m"), (9.0, "9m"), (10.1, "10m")):
    VEHICLE_PARTS[f"decoupler_real_{_tag}"] = {"name": f"Stage separation ({_w:g} m)", "category": "structural", "mass": 0.0,
                                               "height": 0.4, "width": _w}

SITES = {  # longitude, latitude (deg)
    "sriharikota": {"name": "Satish Dhawan Space Centre, Sriharikota", "longitude": 80.23, "latitude": 13.72},
    "canaveral": {"name": "Cape Canaveral / Kennedy Space Center", "longitude": -80.60, "latitude": 28.50},
    "kourou": {"name": "Guiana Space Centre, Kourou", "longitude": -52.77, "latitude": 5.24},
    "baikonur": {"name": "Baikonur Cosmodrome", "longitude": 63.30, "latitude": 45.96},
    "wenchang": {"name": "Wenchang Space Launch Site", "longitude": 110.95, "latitude": 19.61},
    "mahia": {"name": "Rocket Lab Launch Complex 1, Mahia", "longitude": 177.86, "latitude": -39.26},
    "vandenberg": {"name": "Vandenberg Space Force Base", "longitude": -120.61, "latitude": 34.63},
    "tanegashima": {"name": "Tanegashima Space Center", "longitude": 130.97, "latitude": 30.40},
}
