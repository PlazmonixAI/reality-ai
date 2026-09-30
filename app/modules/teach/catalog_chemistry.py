"""ASM Teach chemistry: Class 9 to 12. Chapters follow the NCERT textbooks; ICSE-only topics are tagged with their boards."""
from app.modules.teach.core import X

C = "chemistry"
ICSE = ("ICSE", "State")

# ================================================================ Class 9
X("c9-concentration", 9, C, "Is Matter Around Us Pure?", "Concentration of a solution", "concept",
  "Mass by mass and mass by volume percentage.",
  params="ms:Mass of solute:g:20:0.1:500; mw:Mass of solvent:g:180:1:2000; Vs:Volume of solution:mL:200:1:2000",
  out="mass_pct:Mass by mass percentage:%:100*ms/(ms + mw); mv_pct:Mass by volume percentage:%:100*ms/Vs",
  eqs="mass_pct = 100*ms/(ms + mw)", tags="concentration solution mass percentage solute solvent",
  steps="Mass of solution = mass of solute + mass of solvent | Mass % = mass of solute / mass of solution × 100 | Mass by volume % = mass of solute (g) / volume of solution (mL) × 100",
  ask="mass_pct", lab="molarity")

X("c9-solubility", 9, C, "Is Matter Around Us Pure?", "Solubility and saturated solutions", "concept",
  "How much salt a given amount of water can hold.",
  params="S:Solubility:g per 100 g water:36:1:250; mw:Mass of water:g:50:1:1000; added:Solute added:g:25:0:500",
  out="max_dissolve:Most that can dissolve:g:S*mw/100; excess:Left undissolved:g:Max(0, added - S*mw/100)",
  eqs="max_dissolve = S*mw/100", tags="solubility saturated solution dissolve",
  steps="Solubility is the mass of solute that saturates 100 g of solvent at that temperature | For mw grams of water scale in proportion: S × mw/100 | Anything above that stays undissolved",
  ask="max_dissolve")

X("c9-kelvin", 9, C, "Matter in Our Surroundings", "Celsius and kelvin", "concept",
  "Converting between the two temperature scales.",
  params="Tc:Temperature:degC:25:-273:500",
  out="Tk:Temperature:K:Tc + 273.15", plot="Tc: Tk", eqs="Tk = Tc + 273.15", tags="kelvin celsius temperature scale",
  steps="The kelvin scale starts at absolute zero, −273.15 °C | One kelvin is the same size as one degree Celsius | So T(K) = T(°C) + 273.15", ask="Tk")

X("c9-mole", 9, C, "Atoms and Molecules", "Mole concept", "concept",
  "Moles from mass, and how many particles that is.",
  params="m:Mass:g:36:0.1:1000; M:Molar mass:g/mol:18:1:500",
  out="n:Amount:mol:m/M; Np:Number of particles:-:m/M*N_A", eqs="n = m/M | Np = n*N_A", tags="mole avogadro number molar mass particles",
  steps="One mole of any substance has 6.022 × 10²³ particles | The molar mass M is the mass of one mole in grams | n = m/M, and particles = n × N_A", ask="n,Np")

X("c9-molecular-mass", 9, C, "Atoms and Molecules", "Molecular mass from a formula", "concept",
  "Adding atomic masses: CₓHᵧOz.",
  params="nC:Carbon atoms:-:6:0:20:1; nH:Hydrogen atoms:-:12:0:40:1; nO:Oxygen atoms:-:6:0:20:1; nN:Nitrogen atoms:-:0:0:10:1",
  out="M:Molecular mass:u:12.011*nC + 1.008*nH + 15.999*nO + 14.007*nN; pC:Carbon by mass:%:100*12.011*nC/(12.011*nC + 1.008*nH + 15.999*nO + 14.007*nN)",
  eqs="M = 12*nC + 1*nH + 16*nO + 14*nN", tags="molecular mass formula mass atomic mass glucose",
  steps="Multiply each element's atomic mass by the number of its atoms | Add them up | Glucose C₆H₁₂O₆ comes to 180 u", ask="M")

X("c9-avg-atomic-mass", 9, C, "Structure of the Atom", "Average atomic mass from isotopes", "concept",
  "Why chlorine's atomic mass is 35.5.",
  params="m1:Mass of isotope 1:u:35:1:250; p1:Abundance of isotope 1:%:75:0:100; m2:Mass of isotope 2:u:37:1:250",
  out="Mavg:Average atomic mass:u:m1*p1/100 + m2*(100 - p1)/100", plot="p1: Mavg", eqs="Mavg = m1*p1 + m2*(1 - p1)",
  tags="isotopes average atomic mass abundance chlorine",
  steps="Each isotope contributes its mass times its fraction in nature | Add the contributions | Chlorine: 35 × 0.75 + 37 × 0.25 = 35.5 u", ask="Mavg")

X("c9-shells", 9, C, "Structure of the Atom", "Protons, neutrons and electron shells", "concept",
  "Counting particles and the 2n² rule for shells.",
  params="Z:Atomic number:-:11:1:20:1; A:Mass number:-:23:1:40:1; n:Shell number:-:3:1:4:1",
  out="neutrons:Neutrons:-:A - Z; electrons:Electrons in the neutral atom:-:Z; cap:Most electrons shell n can hold:-:2*n**2",
  eqs="neutrons = A - Z | cap = 2*n**2", scene="atom: n=n, Z=Z", tags="atomic number mass number neutrons bohr bury shells valency",
  steps="Atomic number Z = number of protons = number of electrons in a neutral atom | Mass number A = protons + neutrons | A shell n holds at most 2n² electrons: 2, 8, 18, 32", ask="neutrons")

X("c9-const-proportion", 9, C, "Atoms and Molecules", "Law of constant proportions", "law",
  "Water always has hydrogen and oxygen in the mass ratio 1 : 8.",
  params="mH:Mass of hydrogen:g:2:0.1:100",
  out="mO:Oxygen needed:g:mH*15.999/(2*1.008); mW:Water formed:g:mH + mH*15.999/(2*1.008)", eqs="mO = 8*mH",
  tags="law of constant proportions conservation of mass water",
  steps="In H₂O, 2 × 1.008 g of hydrogen combines with 16.00 g of oxygen | That is a fixed ratio of about 1 : 8 by mass | Mass is conserved, so water formed = hydrogen + oxygen", ask="mO")

# ================================================================ Class 10
X("c10-ph", 10, C, "Acids, Bases and Salts", "pH scale", "concept",
  "pH from hydrogen ion concentration, and the colour of universal indicator.",
  params="logH:log10 of [H⁺] (mol/L):-:-3:-14:0",
  out="H:Hydrogen ion concentration:mol/L:10**logH; pH:pH:-:-logH; pOH:pOH:-:14 + logH; OH:Hydroxide ion concentration:mol/L:10**(-14 - logH)",
  plot="logH: pH", eqs="pH = -log10(H) | pH + pOH = 14", scene="beaker: pH=pH",
  tags="ph scale acid base neutral indicator hydrogen ion", lab="ph", ask="pH",
  steps="pH is minus the log of the hydrogen ion concentration | Each pH unit is a tenfold change | At 25 °C [H⁺][OH⁻] = 10⁻¹⁴, so pH + pOH = 14")

X("c10-dilution", 10, C, "Acids, Bases and Salts", "Diluting an acid", "concept",
  "M₁V₁ = M₂V₂: adding water lowers concentration, not moles.",
  params="M1:Starting concentration:mol/L:2:0.01:18; V1:Volume taken:mL:50:1:1000; V2:Final volume:mL:500:1:5000",
  out="M2:Final concentration:mol/L:M1*V1/V2; water:Water to add:mL:V2 - V1; pH2:pH of a strong monoprotic acid:-:-log(M1*V1/V2)/log(10)",
  plot="V2: M2", eqs="M1*V1 = M2*V2", tags="dilution molarity acid water", lab="molarity",
  steps="Moles of acid n = M × V stay the same when water is added | So M₁V₁ = M₂V₂ | Always add acid to water, not water to acid", ask="M2")

X("c10-neutralisation", 10, C, "Acids, Bases and Salts", "Neutralisation: how much base?", "practical",
  "Volume of NaOH needed to neutralise an acid.",
  params="Ma:Acid concentration:mol/L:0.1:0.01:2; Va:Acid volume:mL:25:1:100; na:H⁺ per acid molecule:-:1:1:3:1; Mb:Base concentration:mol/L:0.1:0.01:2",
  out="Vb:Base volume at the end point:mL:Ma*Va*na/Mb; mol:Moles of H⁺ neutralised:mol:Ma*Va*na/1000",
  eqs="na*Ma*Va = Mb*Vb", scene="beaker: pH=7", tags="neutralisation titration acid base end point", lab="titration",
  steps="At the end point moles of H⁺ = moles of OH⁻ | Moles of H⁺ = na × Ma × Va | Moles of OH⁻ = Mb × Vb | So Vb = na Ma Va / Mb", ask="Vb")

X("c10-decomposition", 10, C, "Chemical Reactions and Equations", "Heating limestone: CaCO₃ → CaO + CO₂", "law",
  "Masses of products from a balanced equation.",
  params="m:Mass of limestone:g:50:1:1000",
  out="mCaO:Quicklime formed:g:m*56.077/100.086; mCO2:Carbon dioxide released:g:m*44.009/100.086; V_CO2:Volume of CO₂ at STP:L:m/100.086*22.414",
  eqs="mCO2 = m*44/100", tags="decomposition reaction calcium carbonate lime stoichiometry",
  steps="CaCO₃ → CaO + CO₂: one mole gives one mole of each | Molar masses 100, 56 and 44 g/mol | Scale by the moles of CaCO₃ taken", ask="mCO2")

X("c10-combustion", 10, C, "Carbon and its Compounds", "Burning a fuel: calorific value", "concept",
  "Heat released by burning a fuel.",
  params="m:Mass of fuel:kg:2:0.01:100; cv:Calorific value:MJ/kg:55:10:150",
  out="Q:Heat released:MJ:m*cv; water:Water it could boil from 25 °C:kg:m*cv*1e6/(4186*75 + 2.26e6)",
  eqs="Q = m*cv", tags="fuel calorific value combustion lpg methane energy",
  steps="Calorific value is the heat released by completely burning 1 kg of fuel | Q = mass × calorific value | LPG is about 55 MJ/kg, wood about 17 MJ/kg", ask="Q")

X("c10-alkane", 10, C, "Carbon and its Compounds", "Homologous series of alkanes", "concept",
  "Each member adds CH₂, or 14 u.",
  params="n:Carbon atoms:-:4:1:10:1",
  out="H:Hydrogen atoms:-:2*n + 2; M:Molecular mass:u:12.011*n + 1.008*(2*n + 2); O2:O₂ needed to burn one mole:mol:(3*n + 1)/2",
  plot="n: M", eqs="M = 14*n + 2", tags="alkane homologous series methane ethane propane butane",
  steps="Alkanes have the formula CₙH₂ₙ₊₂ | Neighbouring members differ by CH₂ = 14 u | Burning: CₙH₂ₙ₊₂ + (3n + 1)/2 O₂ → nCO₂ + (n + 1)H₂O", ask="M")

X("c10-gas-volume", 10, C, "Mole Concept and Stoichiometry", "Molar volume of a gas", "law",
  "One mole of any gas fills 22.4 L at STP.", boards=ICSE,
  params="m:Mass of gas:g:8:0.1:500; M:Molar mass:g/mol:32:2:200",
  out="n:Amount:mol:m/M; V:Volume at STP:L:22.414*m/M; rho:Density at STP:g/L:M/22.414; vd:Vapour density:-:M/2",
  eqs="V = n*22.4 | vd = M/2", tags="molar volume stp avogadro vapour density gas",
  steps="Avogadro's law: equal volumes of gases at the same T and P hold equal numbers of molecules | So one mole of any gas occupies 22.4 L at STP | Vapour density = molar mass / 2", ask="V")

X("c10-percent-comp", 10, C, "Mole Concept and Stoichiometry", "Percentage composition", "concept",
  "Nitrogen in fertilisers: urea against ammonium nitrate.", boards=ICSE,
  params="na:Atoms of the element:-:2:1:10:1; Ar:Atomic mass of the element:u:14:1:200; M:Molar mass of compound:g/mol:60:2:500",
  out="pct:Percentage by mass:%:100*na*Ar/M", eqs="pct = 100*na*Ar/M", tags="percentage composition fertiliser urea nitrogen",
  steps="Mass of the element in one mole = number of atoms × atomic mass | Divide by the molar mass and multiply by 100 | Urea CO(NH₂)₂: 2 × 14/60 = 46.7% nitrogen", ask="pct")

X("c10-electrolysis", 10, C, "Electrolysis", "Faraday's law: mass deposited", "law",
  "Electroplating: how much metal a current deposits.", boards=ICSE,
  params="I:Current:A:2:0.1:20; t:Time:min:30:1:600; M:Molar mass of metal:g/mol:63.5:1:250; z:Charge on the ion:-:2:1:3:1",
  out="Q:Charge passed:C:I*t*60; m:Mass deposited:g:I*t*60*M/(z*F_c)", plot="t: m", eqs="m = I*t*M/(z*F)",
  tags="electrolysis faraday law electroplating copper mass deposited",
  steps="Charge Q = It | Each ion needs z electrons, so moles deposited = Q/(zF) | Mass = moles × M", ask="m")

# ================================================================ Class 11
X("c11-molarity", 11, C, "Some Basic Concepts of Chemistry", "Molarity, molality and mole fraction", "concept",
  "Three ways to state how concentrated a solution is.",
  params="ms:Mass of solute:g:5.85:0.1:500; Ms:Molar mass of solute:g/mol:58.44:1:500; mw:Mass of water:g:100:1:2000; V:Volume of solution:mL:100:1:2000",
  out="n:Moles of solute:mol:ms/Ms; M:Molarity:mol/L:ms/Ms/(V/1000); mb:Molality:mol/kg:ms/Ms/(mw/1000); x:Mole fraction of solute:-:(ms/Ms)/(ms/Ms + mw/18.015)",
  eqs="M = n/V | mb = n/mw", tags="molarity molality mole fraction concentration", lab="molarity",
  steps="Moles of solute n = mass / molar mass | Molarity = n per litre of solution | Molality = n per kilogram of solvent | Mole fraction = n / (n + moles of solvent)", ask="M,mb")

X("c11-limiting", 11, C, "Some Basic Concepts of Chemistry", "Limiting reagent: N₂ + 3H₂ → 2NH₃", "concept",
  "The reactant that runs out first decides how much product forms.",
  params="mN2:Mass of nitrogen:g:28:1:500; mH2:Mass of hydrogen:g:10:1:100",
  out="nN2:Moles of N₂:mol:mN2/28.014; nH2:Moles of H₂:mol:mH2/2.016; nNH3:Ammonia formed:mol:2*Min(mN2/28.014, mH2/(3*2.016)); mNH3:Ammonia formed:g:17.031*2*Min(mN2/28.014, mH2/(3*2.016))",
  eqs="nNH3 = 2*Min(nN2, nH2/3)", tags="limiting reagent stoichiometry ammonia excess", lab="reactants",
  steps="Convert both masses to moles | Divide each by its coefficient: N₂ by 1, H₂ by 3 | The smaller quotient is the limiting reagent | Moles of NH₃ = 2 × that quotient", ask="mNH3")

X("c11-empirical", 11, C, "Some Basic Concepts of Chemistry", "Combustion analysis: carbon and hydrogen", "practical",
  "Percentages of C and H from the CO₂ and H₂O formed.",
  params="ms:Mass of sample:g:0.2:0.01:5; mCO2:CO₂ formed:g:0.44:0.01:10; mH2O:H₂O formed:g:0.18:0.01:10",
  out="pC:Carbon:%:100*mCO2*12.011/(44.009*ms); pH:Hydrogen:%:100*mH2O*2*1.008/(18.015*ms); pO:Oxygen by difference:%:100 - 100*mCO2*12.011/(44.009*ms) - 100*mH2O*2*1.008/(18.015*ms)",
  eqs="pC = 100*(12/44)*mCO2/ms", tags="empirical formula combustion analysis percentage carbon hydrogen",
  steps="All the carbon ends up in CO₂: mass of C = 12/44 × mass of CO₂ | All the hydrogen ends up in H₂O: mass of H = 2/18 × mass of H₂O | Oxygen is what is left", ask="pC")

X("c11-photon", 11, C, "Structure of Atom", "Energy of a photon", "concept",
  "Planck's quantum: E = hν = hc/λ.",
  params="lam:Wavelength:nm:500:100:1000",
  out="nu:Frequency:Hz:c0/(lam*1e-9); E:Energy of one photon:J:h_P*c0/(lam*1e-9); E_mol:Energy of a mole of photons:kJ/mol:h_P*c0/(lam*1e-9)*N_A/1000",
  plot="lam: E_mol", eqs="E = h*nu | c = nu*lam", tags="planck quantum photon energy wavelength frequency",
  steps="Light comes in quanta of energy hν | ν = c/λ | So E = hc/λ; multiply by N_A for a mole", ask="E")

X("c11-bohr-chem", 11, C, "Structure of Atom", "Energy of an electron in hydrogen-like atoms", "concept",
  "Bohr energy levels and the energy needed to ionise.",
  params="n:Principal quantum number:-:1:1:6:1; Z:Nuclear charge:-:1:1:4:1",
  out="E:Energy:J:-2.18e-18*Z**2/n**2; IE:Ionisation energy from level n:kJ/mol:2.18e-18*Z**2/n**2*N_A/1000", plot="n: E",
  eqs="E = -2.18e-18*Z**2/n**2", scene="atom: n=n, Z=Z", tags="bohr energy level hydrogen ionisation energy", lab="hydrogen",
  steps="Bohr's model gives Eₙ = −2.18 × 10⁻¹⁸ Z²/n² J | The negative sign means the electron is bound | Ionisation takes it to n = ∞ where E = 0", ask="E")

X("c11-debroglie", 11, C, "Structure of Atom", "Wave nature: de Broglie wavelength", "concept",
  "Every moving particle has a wavelength; only tiny ones show it.",
  params="m:Mass:kg:9.109e-31:1e-31:1; v:Speed:m/s:1e6:0.1:1e8",
  out="lam:Wavelength:m:h_P/(m*v)", eqs="lam = h/(m*v)", tags="de broglie wavelength dual nature electron",
  steps="De Broglie proposed λ = h/p for any particle | p = mv | For a cricket ball λ is about 10⁻³⁴ m, far too small to observe", ask="lam")

X("c11-uncertainty", 11, C, "Structure of Atom", "Heisenberg's uncertainty principle", "concept",
  "The more exactly position is known, the less exactly speed is.",
  params="m:Mass:kg:9.109e-31:1e-31:1; dx:Uncertainty in position:m:1e-10:1e-15:1",
  out="dv:Minimum uncertainty in speed:m/s:h_P/(4*pi*m*dx)", eqs="dx*m*dv = h/(4*pi)", tags="heisenberg uncertainty principle position momentum",
  steps="Δx × Δp ≥ h/4π | Δp = mΔv | So Δv ≥ h/(4πmΔx)", ask="dv")

X("c11-dipole", 11, C, "Chemical Bonding and Molecular Structure", "Dipole moment and ionic character", "concept",
  "Percentage ionic character of a polar bond.",
  params="mu_obs:Observed dipole moment:D:1.03:0:12; d:Bond length:pm:127:50:300",
  out="mu_ionic:Dipole moment if fully ionic:D:e_c*d*1e-12/3.33564e-30; ionic:Percentage ionic character:%:100*mu_obs/(e_c*d*1e-12/3.33564e-30)",
  eqs="mu = q*d", tags="dipole moment debye polar bond ionic character hcl",
  steps="Dipole moment = charge × separation | A fully ionic bond would have charges ±e at the bond length | % ionic character = observed μ / ionic μ × 100 | 1 D = 3.336 × 10⁻³⁰ C m", ask="ionic")

X("c11-bond-order", 11, C, "Chemical Bonding and Molecular Structure", "Bond order from molecular orbitals", "concept",
  "Stability and magnetism of O₂, N₂ and their ions.",
  params="Nb:Electrons in bonding orbitals:-:10:0:16:1; Na:Electrons in antibonding orbitals:-:6:0:16:1",
  out="bo:Bond order:-:(Nb - Na)/2", eqs="bo = (Nb - Na)/2", tags="molecular orbital theory bond order oxygen nitrogen stability",
  steps="Bonding electrons hold the atoms together; antibonding electrons pull them apart | Bond order = ½(Nb − Na) | O₂: ½(10 − 6) = 2 | Higher bond order means a shorter, stronger bond", ask="bo")

X("c11-ideal-gas", 11, C, "States of Matter", "Ideal gas equation", "law",
  "PV = nRT for any amount of gas.",
  params="n:Amount:mol:1:0.01:10; T:Temperature:K:273.15:50:1000; V:Volume:L:22.4:0.5:100",
  out="P:Pressure:atm:n*0.082057*T/V; P_kPa:Pressure:kPa:n*8.314462*T/V", plot="V: P", eqs="P*V = n*R*T", scene="gas: P=P, V=V, T=T",
  tags="ideal gas equation pressure volume temperature moles", lab="gas", ask="P",
  steps="Combine Boyle's, Charles's and Avogadro's laws | PV = nRT | R = 0.0821 L atm/(mol K) = 8.314 J/(mol K)")

X("c11-boyle", 11, C, "States of Matter", "Boyle's law", "law",
  "At constant temperature, pressure and volume are inversely related.",
  params="P1:Initial pressure:atm:1:0.1:10; V1:Initial volume:L:10:0.5:100; V2:Final volume:L:5:0.5:100",
  out="P2:Final pressure:atm:P1*V1/V2", plot="V2: P2", eqs="P1*V1 = P2*V2", scene="gas: P=P2, V=V2, T=300",
  tags="boyle law pressure volume isotherm", lab="gas", ask="P2",
  steps="At fixed temperature and amount, PV is constant | So P₁V₁ = P₂V₂ | The P-V graph is a hyperbola")

X("c11-charles", 11, C, "States of Matter", "Charles's law", "law",
  "At constant pressure, volume is proportional to kelvin temperature.",
  params="V1:Initial volume:L:10:0.5:100; T1:Initial temperature:K:300:50:1000; T2:Final temperature:K:400:50:1000",
  out="V2:Final volume:L:V1*T2/T1", plot="T2: V2", eqs="V1/T1 = V2/T2", scene="gas: P=1, V=V2, T=T2",
  tags="charles law volume temperature absolute zero", lab="gas", ask="V2",
  steps="At fixed pressure V ∝ T (in kelvin) | V₁/T₁ = V₂/T₂ | Extending the line to V = 0 gives absolute zero, −273.15 °C")

X("c11-dalton", 11, C, "States of Matter", "Dalton's law of partial pressures", "law",
  "Each gas in a mixture pushes as if it were alone.",
  params="n1:Moles of gas 1:mol:2:0:10; n2:Moles of gas 2:mol:3:0:10; P:Total pressure:atm:5:0.1:50",
  out="x1:Mole fraction of gas 1:-:n1/(n1 + n2); p1:Partial pressure of gas 1:atm:P*n1/(n1 + n2); p2:Partial pressure of gas 2:atm:P*n2/(n1 + n2)",
  eqs="p1 = x1*P | P = p1 + p2", tags="dalton partial pressure mole fraction gas mixture",
  steps="Total pressure = sum of partial pressures | Each partial pressure is proportional to that gas's moles | pᵢ = xᵢP", ask="p1")

X("c11-graham", 11, C, "States of Matter", "Graham's law of diffusion", "law",
  "Lighter gases spread faster.",
  params="M1:Molar mass of gas 1:g/mol:2:1:200; M2:Molar mass of gas 2:g/mol:32:1:200",
  out="ratio:Rate of gas 1 / rate of gas 2:-:sqrt(M2/M1)", eqs="r1/r2 = sqrt(M2/M1)", tags="graham law diffusion effusion molar mass",
  steps="At the same temperature all gases have the same mean kinetic energy ½Mv² | So v ∝ 1/√M | Rates of diffusion follow the same ratio", ask="ratio")

X("c11-vdw", 11, C, "States of Matter", "Real gases: van der Waals equation", "concept",
  "Attractions lower the pressure; molecular volume raises it.",
  params="n:Amount:mol:1:0.1:10; T:Temperature:K:300:100:1000; V:Volume:L:1:0.1:50; a:Attraction constant a:L^2*atm/mol^2:3.59:0:20; b:Volume constant b:L/mol:0.0427:0:0.2",
  out="P_real:Van der Waals pressure:atm:n*0.082057*T/(V - n*b) - a*n**2/V**2; P_ideal:Ideal gas pressure:atm:n*0.082057*T/V; Zc:Compressibility factor:-:(n*0.082057*T/(V - n*b) - a*n**2/V**2)*V/(n*0.082057*T)",
  plot="V: P_real, P_ideal", eqs="(P + a*n**2/V**2)*(V - n*b) = n*R*T", tags="van der waals real gas compressibility factor deviation", lab="realgas", ask="P_real",
  steps="Molecules take up space, so the free volume is V − nb | Attractions reduce the pressure on the walls by an/V² squared: an²/V² | Correcting PV = nRT gives (P + an²/V²)(V − nb) = nRT")

X("c11-first-law", 11, C, "Thermodynamics", "First law: heat, work and internal energy", "law",
  "Energy is conserved: ΔU = q + w.",
  params="q:Heat absorbed by the system:J:500:-5000:5000; P:External pressure:kPa:100:1:1000; dV:Volume increase:L:2:-20:20",
  out="w:Work done on the system:J:-P*dV; dU:Change in internal energy:J:q - P*dV", eqs="dU = q + w | w = -P*dV",
  tags="first law thermodynamics internal energy work heat", ask="dU",
  steps="Heat added to the system raises its energy | When the gas expands against pressure P it does work PΔV on the surroundings | So w = −PΔV and ΔU = q − PΔV | kPa × L = J")

X("c11-dh-du", 11, C, "Thermodynamics", "Enthalpy and internal energy", "concept",
  "ΔH = ΔU + Δn_g RT for reactions with gases.",
  params="dU:Change in internal energy:kJ/mol:-890:-3000:3000; dng:Change in moles of gas:-:-2:-5:5:1; T:Temperature:K:298:200:1000",
  out="dH:Enthalpy change:kJ/mol:dU + dng*R_g*T/1000", eqs="dH = dU + dng*R*T", tags="enthalpy internal energy delta n gas",
  steps="H = U + PV | For ideal gases PV = nRT, so Δ(PV) = Δn_g RT at constant T | ΔH = ΔU + Δn_g RT", ask="dH")

X("c11-gibbs", 11, C, "Thermodynamics", "Gibbs energy and spontaneity", "law",
  "When does a reaction go by itself? ΔG = ΔH − TΔS.",
  params="dH:Enthalpy change:kJ/mol:178:-500:500; dS:Entropy change:J/(mol*K):161:-500:500; T:Temperature:K:298:100:2000",
  out="dG:Gibbs energy change:kJ/mol:dH - T*dS/1000; Tc:Crossover temperature:K:1000*dH/dS; K:Equilibrium constant:-:exp(-(dH - T*dS/1000)*1000/(R_g*T))",
  plot="T: dG", eqs="dG = dH - T*dS | dG = -R*T*log(K)", tags="gibbs free energy spontaneity entropy enthalpy equilibrium constant",
  steps="A process is spontaneous at constant T and P when ΔG < 0 | ΔG = ΔH − TΔS | The sign changes at T = ΔH/ΔS | ΔG° = −RT ln K", ask="dG")

X("c11-calorimeter", 11, C, "Thermodynamics", "Bomb calorimeter", "practical",
  "Heat of combustion from a temperature rise.",
  params="Ccal:Heat capacity of calorimeter:kJ/K:10:1:50; dT:Temperature rise:K:2.5:0.1:20; m:Mass burned:g:1:0.01:10; M:Molar mass:g/mol:180:2:500",
  out="q:Heat released:kJ:Ccal*dT; dU:Internal energy of combustion:kJ/mol:-Ccal*dT*M/m", eqs="q = Ccal*dT",
  tags="bomb calorimeter heat of combustion internal energy", ask="dU",
  steps="Heat released raises the calorimeter temperature: q = C ΔT | At constant volume this is ΔU | Divide by moles burned (m/M) for the molar value")

X("c11-kp-kc", 11, C, "Equilibrium", "Kp and Kc", "concept",
  "Converting between pressure and concentration equilibrium constants.",
  params="Kc:Kc:-:0.5:1e-6:1e6; dng:Change in moles of gas:-:-2:-4:4:1; T:Temperature:K:500:200:2000",
  out="Kp:Kp:-:Kc*(0.0831446*T)**dng", eqs="Kp = Kc*(R*T)**dng", tags="kp kc equilibrium constant gas",
  steps="For each gas p = cRT | Substitute into Kp | Kp = Kc(RT)^Δn with R = 0.0831 L bar/(mol K)", ask="Kp")

X("c11-weak-acid", 11, C, "Equilibrium", "Degree of dissociation of a weak acid", "derivation",
  "pH of acetic acid from Ka and concentration.",
  params="Ka:Ka:-:1.8e-5:1e-10:0.1; C:Concentration:mol/L:0.1:0.0001:2",
  out="alpha:Degree of dissociation:-:(-Ka + sqrt(Ka**2 + 4*Ka*C))/(2*C); H:[H⁺]:mol/L:(-Ka + sqrt(Ka**2 + 4*Ka*C))/2; pH:pH:-:-log((-Ka + sqrt(Ka**2 + 4*Ka*C))/2)/log(10)",
  plot="C: pH", eqs="Ka = C*alpha**2/(1 - alpha)", scene="beaker: pH=pH", tags="weak acid ostwald dilution law degree of dissociation ph acetic",
  lab="ph", ask="pH,alpha",
  steps="HA ⇌ H⁺ + A⁻: at equilibrium [H⁺] = [A⁻] = Cα and [HA] = C(1 − α) | Ka = Cα²/(1 − α) | Solve the quadratic Cα² + Kaα − Ka = 0 | When α is small, α ≈ √(Ka/C)")

X("c11-strong-acid", 11, C, "Equilibrium", "pH of a strong acid or base", "concept",
  "Complete dissociation makes the pH easy.",
  params="C:Concentration:mol/L:0.01:1e-6:1; base:Base? (0 acid, 1 base):-:0:0:1:1",
  out="pH:pH:-:(1 - base)*(-log(C)/log(10)) + base*(14 + log(C)/log(10))", eqs="pH = -log10(C)", scene="beaker: pH=pH",
  tags="strong acid strong base ph hcl naoh", lab="ph",
  steps="A strong acid dissociates completely, so [H⁺] = C | pH = −log C | For a strong base pOH = −log C and pH = 14 − pOH", ask="pH")

X("c11-buffer", 11, C, "Equilibrium", "Buffer solutions: Henderson equation", "law",
  "A buffer holds its pH steady.",
  params="pKa:pKa of the acid:-:4.76:2:12; salt:Salt concentration:mol/L:0.1:0.001:2; acid:Acid concentration:mol/L:0.1:0.001:2",
  out="pH:pH:-:pKa + log(salt/acid)/log(10)", plot="salt: pH", eqs="pH = pKa + log10(salt/acid)", scene="beaker: pH=pH",
  tags="buffer henderson hasselbalch pka", lab="buffers", ask="pH",
  steps="Ka = [H⁺][A⁻]/[HA] | Take −log: pH = pKa + log([A⁻]/[HA]) | The salt supplies A⁻ and the weak acid stays mostly undissociated")

X("c11-ksp", 11, C, "Equilibrium", "Solubility product", "concept",
  "Molar solubility of sparingly soluble salts.",
  params="Ksp:Solubility product:-:1.8e-10:1e-40:1e-2; kind:Salt type (1 for AB, 2 for AB₂):-:1:1:2:1; M:Molar mass:g/mol:143.3:10:500",
  out="s:Molar solubility:mol/L:(2 - kind)*sqrt(Ksp) + (kind - 1)*(Ksp/4)**(1/3); s_g:Solubility:g/L:M*((2 - kind)*sqrt(Ksp) + (kind - 1)*(Ksp/4)**(1/3))",
  eqs="Ksp = s**2 | Ksp = 4*s**3", tags="solubility product ksp silver chloride",
  steps="AB ⇌ A⁺ + B⁻: Ksp = s × s = s² | AB₂ ⇌ A²⁺ + 2B⁻: Ksp = s × (2s)² = 4s³ | Solve for s", ask="s")

X("c11-dou", 11, C, "Organic Chemistry: Some Basic Principles", "Degree of unsaturation", "concept",
  "Rings and π bonds from a molecular formula.",
  params="nC:Carbon atoms:-:6:1:20:1; nH:Hydrogen and halogen atoms:-:6:0:42:1; nN:Nitrogen atoms:-:0:0:4:1",
  out="dou:Degree of unsaturation:-:nC - nH/2 + nN/2 + 1", eqs="dou = nC - nH/2 + nN/2 + 1", tags="degree of unsaturation double bond equivalent ring benzene",
  steps="A saturated open chain CₙH₂ₙ₊₂ has DoU = 0 | Each ring or π bond removes two hydrogens | Count halogens with H; each N adds one H | Benzene C₆H₆: 6 − 3 + 1 = 4", ask="dou")

X("c11-reaction-quotient", 11, C, "Equilibrium", "Le Chatelier and the reaction quotient", "concept",
  "Q against K tells which way a reaction moves.",
  params="K:Equilibrium constant:-:10:1e-4:1e4; A:[A]:mol/L:1:0.001:10; B:[B]:mol/L:2:0.001:10",
  out="Qr:Reaction quotient for A ⇌ B:-:B/A; direction:Q/K (below 1 means forward):-:B/A/K; dG:ΔG at 298 K:kJ/mol:R_g*298*log(B/A/K)/1000",
  eqs="Qr = B/A | dG = R*T*log(Qr/K)", tags="le chatelier reaction quotient equilibrium direction", lab="equilibrium",
  steps="Q has the same form as K but uses the present concentrations | Q < K: the reaction moves forward | Q > K: it moves backward | ΔG = RT ln(Q/K)", ask="Qr")

# ================================================================ Class 12
X("c12-raoult", 12, C, "Solutions", "Raoult's law for two liquids", "law",
  "Vapour pressure of an ideal solution.",
  params="pA:Vapour pressure of pure A:kPa:12:0.1:200; pB:Vapour pressure of pure B:kPa:3:0.1:200; xA:Mole fraction of A in the liquid:-:0.4:0:1",
  out="p:Total vapour pressure:kPa:xA*pA + (1 - xA)*pB; yA:Mole fraction of A in the vapour:-:xA*pA/(xA*pA + (1 - xA)*pB)",
  plot="xA: p", eqs="p = xA*pA + xB*pB", tags="raoult law vapour pressure ideal solution", lab="vapor", ask="p",
  steps="Each component's partial pressure is its mole fraction times its pure vapour pressure | p_A = x_A p°_A | Total pressure is the sum, a straight line in x_A | The vapour is richer in the more volatile liquid")

X("c12-henry", 12, C, "Solutions", "Henry's law: gas in a liquid", "law",
  "Why soda fizzes when opened.",
  params="KH:Henry's constant:MPa:167:1:10000; p:Partial pressure of gas:kPa:250:1:1000",
  out="x:Mole fraction dissolved:-:p/(KH*1000); mol_L:Dissolved gas:mol/L:p/(KH*1000)*55.5", plot="p: x", eqs="p = KH*x",
  tags="henry law solubility of gases carbonated drinks", ask="x",
  steps="The solubility of a gas is proportional to its partial pressure above the liquid | p = K_H x | Opening a bottle lowers p, so CO₂ comes out")

X("c12-bp", 12, C, "Solutions", "Elevation of boiling point", "law",
  "Salt water boils above 100 °C.",
  params="Kb:Ebullioscopic constant:K*kg/mol:0.512:0.1:5; w2:Mass of solute:g:10:0.1:200; M2:Molar mass of solute:g/mol:58.44:10:500; w1:Mass of solvent:g:200:10:2000; i:Van't Hoff factor:-:2:1:4",
  out="mb:Molality:mol/kg:w2/M2/(w1/1000); dTb:Boiling point rise:K:i*Kb*w2/M2/(w1/1000)", plot="w2: dTb", eqs="dTb = i*Kb*mb",
  tags="boiling point elevation colligative property molality", lab="colligative", ask="dTb",
  steps="A non-volatile solute lowers the vapour pressure | The solution must be hotter to reach atmospheric pressure | ΔT_b = i K_b m")

X("c12-fp", 12, C, "Solutions", "Depression of freezing point", "law",
  "Why salt melts ice on roads.",
  params="Kf:Cryoscopic constant:K*kg/mol:1.86:0.5:40; w2:Mass of solute:g:10:0.1:200; M2:Molar mass of solute:g/mol:58.44:10:500; w1:Mass of solvent:g:200:10:2000; i:Van't Hoff factor:-:2:1:4",
  out="mb:Molality:mol/kg:w2/M2/(w1/1000); dTf:Freezing point fall:K:i*Kf*w2/M2/(w1/1000)", plot="w2: dTf", eqs="dTf = i*Kf*mb",
  tags="freezing point depression colligative antifreeze", lab="colligative", ask="dTf",
  steps="The solute lowers the vapour pressure of the liquid but not of the solid | They become equal at a lower temperature | ΔT_f = i K_f m")

X("c12-osmotic", 12, C, "Solutions", "Osmotic pressure", "law",
  "The pressure needed to stop osmosis.",
  params="C:Concentration:mol/L:0.1:0.001:2; T:Temperature:K:298:273:373; i:Van't Hoff factor:-:1:1:4",
  out="Pi:Osmotic pressure:atm:i*C*0.082057*T; Pi_kPa:Osmotic pressure:kPa:i*C*8.314462*T", plot="C: Pi", eqs="Pi = i*C*R*T",
  tags="osmotic pressure osmosis van t hoff colligative", ask="Pi",
  steps="Van 't Hoff: osmotic pressure behaves like gas pressure | π = CRT, times i for electrolytes | Measured at room temperature, it is good for finding molar masses of proteins")

X("c12-molar-mass", 12, C, "Solutions", "Molar mass from boiling point rise", "practical",
  "Using a colligative property to weigh molecules.",
  params="Kb:Ebullioscopic constant:K*kg/mol:2.53:0.1:5; w2:Mass of solute:g:1:0.01:50; w1:Mass of solvent:g:50:5:500; dTb:Observed boiling point rise:K:0.2:0.01:5",
  out="M2:Molar mass of solute:g/mol:Kb*w2*1000/(dTb*w1)", eqs="M2 = Kb*w2*1000/(dTb*w1)", tags="molar mass determination colligative boiling point benzene",
  steps="ΔT_b = K_b × (w₂/M₂)/(w₁/1000) | Rearrange for M₂ | M₂ = K_b w₂ × 1000 / (ΔT_b w₁)", ask="M2")

X("c12-nernst", 12, C, "Electrochemistry", "Nernst equation", "law",
  "Cell potential at any concentration.",
  params="E0:Standard cell potential:V:1.10:-3:3; n:Electrons transferred:-:2:1:6:1; logQ:log10 of reaction quotient:-:0:-6:6; T:Temperature:K:298:273:373",
  out="E:Cell potential:V:E0 - R_g*T/(n*F_c)*log(10)*logQ; slope:RT ln10 / nF:V:R_g*T*log(10)/(n*F_c)", plot="logQ: E",
  eqs="E = E0 - (0.0591/n)*log10(Q)", tags="nernst equation cell potential daniell cell concentration", lab="galvanic", ask="E",
  steps="ΔG = ΔG° + RT ln Q | With ΔG = −nFE: −nFE = −nFE° + RT ln Q | E = E° − (RT/nF) ln Q | At 298 K this is E° − (0.0591/n) log Q")

X("c12-cell-gibbs", 12, C, "Electrochemistry", "Cell potential, Gibbs energy and K", "concept",
  "A positive E° means a spontaneous cell reaction.",
  params="E0:Standard cell potential:V:1.10:-2:3; n:Electrons transferred:-:2:1:6:1",
  out="dG:Standard Gibbs energy:kJ/mol:-n*F_c*E0/1000; log10K:log10 of K:-:n*F_c*E0/(R_g*298.15*log(10))", eqs="dG = -n*F*E0 | log10(K) = n*E0/0.0591",
  tags="gibbs energy cell potential equilibrium constant", ask="dG",
  steps="Electrical work nFE equals the fall in Gibbs energy | ΔG° = −nFE° | Also ΔG° = −RT ln K, so log K = nE°/0.0591 at 298 K")

X("c12-conductivity", 12, C, "Electrochemistry", "Molar conductivity", "concept",
  "Conductivity per mole of electrolyte.",
  params="kappa:Conductivity:S/cm:0.0129:1e-6:1; C:Concentration:mol/L:0.1:0.0001:2",
  out="Lm:Molar conductivity:S*cm^2/mol:1000*kappa/C", eqs="Lm = 1000*kappa/C", tags="molar conductivity conductance electrolyte",
  steps="Molar conductivity is the conductivity of a solution containing one mole between electrodes 1 cm apart | Λm = κ × 1000/C with C in mol/L", ask="Lm")

X("c12-kohlrausch", 12, C, "Electrochemistry", "Kohlrausch: strong electrolytes", "practical",
  "Molar conductivity falls with √C for strong electrolytes.",
  params="L0:Limiting molar conductivity:S*cm^2/mol:126.4:50:500; A:Slope A:S*cm^2*L^0.5/mol^1.5:89:10:300; C:Concentration:mol/L:0.01:0:0.2",
  out="Lm:Molar conductivity:S*cm^2/mol:L0 - A*sqrt(C)", plot="C: Lm", eqs="Lm = L0 - A*sqrt(C)", tags="kohlrausch law limiting molar conductivity strong electrolyte",
  steps="Ions interfere with each other more in concentrated solutions | For strong electrolytes Λm = Λ°m − A√C | Plotting Λm against √C and extending to C = 0 gives Λ°m", ask="Lm")

X("c12-faraday", 12, C, "Electrochemistry", "Faraday's laws of electrolysis", "law",
  "Mass of product from charge passed.",
  params="I:Current:A:1.5:0.01:50; t:Time:min:30:1:1000; M:Molar mass:g/mol:63.55:1:250; n:Electrons per ion:-:2:1:4:1",
  out="Q:Charge:C:I*t*60; m:Mass deposited:g:I*t*60*M/(n*F_c); ne:Moles of electrons:mol:I*t*60/F_c", plot="t: m", eqs="m = M*I*t/(n*F)",
  tags="faraday laws electrolysis mass deposited charge", ask="m",
  steps="One faraday (96,485 C) is a mole of electrons | Moles of metal = moles of electrons / n | Mass = moles × M")

X("c12-first-order", 12, C, "Chemical Kinetics", "First order reactions", "derivation",
  "Integrated rate law and half-life.",
  params="A0:Initial concentration:mol/L:1:0.01:10; k:Rate constant:1/s:0.05:0.0001:5; t:Time:s:20:0:1000",
  out="A:Concentration left:mol/L:A0*exp(-k*t); t_half:Half-life:s:log(2)/k; pct:Percent reacted:%:100*(1 - exp(-k*t))",
  series="At:Concentration:mol/L:A0*exp(-k*tt)", plot="tt=0..5*log(2)/k: At", eqs="A = A0*exp(-k*t) | t_half = log(2)/k | k = (2.303/t)*log10(A0/A)",
  tags="first order reaction integrated rate law half life", lab="kinetics", ask="A,t_half",
  steps="Rate = −d[A]/dt = k[A] | Separate: d[A]/[A] = −k dt | Integrate: ln([A]/[A]₀) = −kt | Half-life: t½ = ln 2 / k, independent of starting concentration")

X("c12-zero-order", 12, C, "Chemical Kinetics", "Zero order reactions", "derivation",
  "Concentration falls in a straight line.",
  params="A0:Initial concentration:mol/L:1:0.1:10; k:Rate constant:mol/(L*s):0.01:0.001:0.05; t:Time:s:30:0:100",
  out="A:Concentration left:mol/L:Max(0, A0 - k*t); t_half:Half-life:s:A0/(2*k)",
  series="At:Concentration:mol/L:Max(0, A0 - k*tt)", plot="tt=0..A0/k: At", eqs="A = A0 - k*t | t_half = A0/(2*k)",
  tags="zero order reaction integrated rate law", lab="kinetics", ask="A,t_half",
  steps="Rate = −d[A]/dt = k, a constant | Integrate: [A] = [A]₀ − kt | t½ = [A]₀/2k grows with starting concentration")

X("c12-rate-law", 12, C, "Chemical Kinetics", "Rate law and order of reaction", "concept",
  "Rate = k[A]ᵐ[B]ⁿ: how each concentration affects the rate.",
  params="k:Rate constant:-:0.5:0.001:10; A:[A]:mol/L:0.2:0.001:2; B:[B]:mol/L:0.1:0.001:2; m:Order in A:-:1:0:3:1; n:Order in B:-:2:0:3:1",
  out="rate:Rate:mol/(L*s):k*A**m*B**n; order:Overall order:-:m + n; x2A:Factor if [A] doubles:-:2**m", plot="A: rate",
  eqs="rate = k*A**m*B**n", tags="rate law order of reaction rate constant", ask="rate",
  steps="The orders m and n are found by experiment, not from the balanced equation | Doubling [A] multiplies the rate by 2ᵐ | Overall order is m + n")

X("c12-arrhenius", 12, C, "Chemical Kinetics", "Arrhenius equation", "law",
  "Rate constants rise steeply with temperature.",
  params="Ap:Pre-exponential factor:1/s:1e13:1e6:1e16; Ea:Activation energy:kJ/mol:75:10:250; T:Temperature:K:300:250:800",
  out="k:Rate constant:1/s:Ap*exp(-Ea*1000/(R_g*T)); frac:Fraction of collisions with enough energy:-:exp(-Ea*1000/(R_g*T))",
  plot="T: k", eqs="k = Ap*exp(-Ea/(R*T))", tags="arrhenius activation energy temperature rate constant", lab="profile", ask="k",
  steps="Only molecules with energy above Ea react | The Boltzmann fraction of such molecules is e^(−Ea/RT) | k = A e^(−Ea/RT)")

X("c12-arrhenius-two", 12, C, "Chemical Kinetics", "Activation energy from two temperatures", "practical",
  "The rule of thumb: rate doubles for every 10 °C.",
  params="k1:Rate constant at T1:1/s:0.02:1e-6:100; T1:T1:K:300:250:600; T2:T2:K:310:250:700; Ea:Activation energy:kJ/mol:53.6:5:250",
  out="k2:Rate constant at T2:1/s:k1*exp(Ea*1000/R_g*(1/T1 - 1/T2)); ratio:k2/k1:-:exp(Ea*1000/R_g*(1/T1 - 1/T2))",
  eqs="log10(k2/k1) = Ea/(2.303*R)*(1/T1 - 1/T2)", tags="activation energy two temperatures arrhenius", ask="k2",
  steps="Write ln k = ln A − Ea/RT at both temperatures | Subtract: ln(k₂/k₁) = (Ea/R)(1/T₁ − 1/T₂) | In log₁₀ form divide by 2.303")

X("c12-spin-moment", 12, C, "The d- and f-Block Elements", "Spin-only magnetic moment", "concept",
  "Magnetic moment from the number of unpaired electrons.",
  params="n:Unpaired electrons:-:5:0:7:1",
  out="mu:Magnetic moment:BM:sqrt(n*(n + 2))", plot="n: mu", eqs="mu = sqrt(n*(n + 2))", tags="magnetic moment unpaired electrons transition metals bohr magneton",
  steps="Each unpaired electron's spin contributes to the moment | μ = √(n(n + 2)) Bohr magnetons | Mn²⁺ (d⁵, five unpaired) gives 5.92 BM", ask="mu")

X("c12-cfse", 12, C, "Coordination Compounds", "Crystal field stabilisation energy", "concept",
  "Octahedral splitting: t₂g and e_g electrons.",
  params="t2g:Electrons in t₂g:-:6:0:6:1; eg:Electrons in e_g:-:0:0:4:1; D0:Splitting Δₒ:kJ/mol:200:50:500",
  out="cfse:CFSE:kJ/mol:(-0.4*t2g + 0.6*eg)*D0; cfse_D:CFSE in units of Δₒ:-:-0.4*t2g + 0.6*eg", eqs="cfse = (-0.4*t2g + 0.6*eg)*D0",
  tags="crystal field theory splitting cfse octahedral strong field weak field",
  steps="In an octahedral field the d orbitals split: t₂g lowered by 0.4Δₒ, e_g raised by 0.6Δₒ | Add the contributions of all d electrons | Low-spin d⁶ (t₂g⁶) gives −2.4Δₒ", ask="cfse")

X("c12-unit-cell", 12, C, "The Solid State", "Density of a cubic crystal", "concept",
  "ρ = ZM / (a³ N_A).", boards=ICSE,
  params="Zc:Atoms per unit cell (1 sc, 2 bcc, 4 fcc):-:4:1:4:1; M:Molar mass:g/mol:63.55:1:300; a:Edge length:pm:361:100:1000",
  out="rho:Density:g/cm^3:Zc*M/((a*1e-10)**3*N_A)", eqs="rho = Zc*M/(a**3*N_A)", tags="unit cell density fcc bcc crystal lattice",
  steps="Mass in one unit cell = Z × M / N_A | Volume = a³ (convert pm to cm) | Density = mass / volume | Copper (fcc, a = 361 pm) gives 8.9 g/cm³", ask="rho")

X("c12-beer", 12, C, "Solutions", "Colorimetry: Beer-Lambert law", "practical",
  "Absorbance grows with concentration and path length.", boards=ICSE,
  params="eps:Molar absorptivity:L/(mol*cm):1000:1:100000; l:Path length:cm:1:0.1:10; C:Concentration:mmol/L:0.5:0:5",
  out="A:Absorbance:-:eps*l*C/1000; T:Transmittance:%:100*10**(-eps*l*C/1000)", plot="C: A", eqs="A = eps*l*C",
  tags="beer lambert absorbance colorimetry transmittance", lab="beers", ask="A",
  steps="Each thin layer absorbs the same fraction of the light reaching it | This gives I = I₀ 10^(−εlc) | Absorbance A = log(I₀/I) = εlc")

X("c12-half-life-drug", 12, C, "Chemical Kinetics", "Drug in the body: repeated first order decay", "concept",
  "How much of a medicine is left after some hours.",
  params="dose:Dose:mg:500:10:2000; t_half:Half-life:h:4:0.5:24; t:Time since dose:h:6:0:48",
  out="left:Amount left:mg:dose*(1/2)**(t/t_half); k:Rate constant:1/h:log(2)/t_half",
  series="mt:Amount left:mg:dose*(1/2)**(tt/t_half)", plot="tt=0..6*t_half: mt", eqs="left = dose*(1/2)**(t/t_half)",
  tags="first order elimination drug half life medicine", scene="decay: N0=dose, N=left, half=t_half", ask="left",
  steps="Elimination of most drugs is first order | After every half-life half is left | Amount = dose × (½)^(t/t½)")
