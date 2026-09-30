"""ASM Teach physics: Class 9 to 12. Chapters follow the NCERT textbooks; ICSE-only topics are tagged with their boards."""
from app.modules.teach.core import X

P = "physics"
ICSE = ("ICSE", "State")

# ================================================================ Class 9
X("p9-speed", 9, P, "Motion", "Average speed and velocity", "concept",
  "Distance over time, and why speed and velocity differ on a round trip.",
  params="d:Distance travelled:m:1200:10:5000; s_net:Displacement:m:400:0:5000; t:Time taken:s:300:10:3600",
  out="v_avg:Average speed:m/s:d/t; vel:Average velocity:m/s:s_net/t; kmh:Average speed:km/h:3.6*d/t",
  eqs="v_avg = d/t | vel = s_net/t", tags="speed velocity distance displacement kmph",
  steps="Average speed is total distance divided by total time | Average velocity uses displacement, so it can be smaller than speed | Multiply m/s by 3.6 to get km/h",
  ask="v_avg,vel")

X("p9-first-eq", 9, P, "Motion", "First equation of motion: v = u + at", "derivation",
  "Velocity grows in a straight line with time when acceleration is uniform.",
  params="u:Initial velocity:m/s:5:0:40; a:Acceleration:m/s^2:2:-5:10; t:Time:s:6:0:30",
  out="v:Final velocity:m/s:u + a*t", plot="t: v", scene="path",
  eqs="v = u + a*t | a = (v - u)/t", tags="equation of motion velocity time graph",
  steps="Acceleration is the change in velocity per unit time: a = (v - u)/t | Multiply both sides by t: at = v - u | Add u to both sides: v = u + at | On a velocity-time graph this is a straight line of slope a and intercept u",
  lab="projectile")

X("p9-second-eq", 9, P, "Motion", "Second equation of motion: s = ut + ½at²", "derivation",
  "Displacement is the area under the velocity-time graph.",
  params="u:Initial velocity:m/s:4:0:40; a:Acceleration:m/s^2:2:-5:10; t:Time:s:5:0:30",
  out="s:Displacement:m:u*t + a*t**2/2; v:Final velocity:m/s:u + a*t", plot="t: s", scene="path",
  eqs="s = u*t + a*t**2/2", tags="equation of motion displacement area under graph",
  steps="Displacement equals the area under the v-t graph from 0 to t | The area is a rectangle u × t plus a triangle ½ × t × (v − u) | Since v − u = at, the triangle is ½at² | So s = ut + ½at²",
  ask="s")

X("p9-third-eq", 9, P, "Motion", "Third equation of motion: v² = u² + 2as", "derivation",
  "Speed after covering a distance, without knowing the time.",
  params="u:Initial velocity:m/s:10:0:40; a:Acceleration:m/s^2:3:0.5:10; s:Displacement:m:50:0:500",
  out="v:Final velocity:m/s:sqrt(u**2 + 2*a*s); t:Time taken:s:(sqrt(u**2 + 2*a*s) - u)/a", plot="s: v",
  eqs="v**2 = u**2 + 2*a*s", tags="equation of motion velocity displacement",
  steps="From the first equation, t = (v − u)/a | Put this t into s = ut + ½at² | Simplify: 2as = v² − u² | So v² = u² + 2as")

X("p9-stopping", 9, P, "Motion", "Stopping distance of a car", "concept",
  "Thinking distance plus braking distance, and why it grows so fast with speed.",
  params="kmh:Speed:km/h:60:10:140; tr:Reaction time:s:0.8:0.3:2; b:Braking deceleration:m/s^2:6:2:9",
  out="u:Speed:m/s:kmh/3.6; d_think:Thinking distance:m:u*tr; d_brake:Braking distance:m:u**2/(2*b); d_stop:Stopping distance:m:d_think + d_brake",
  plot="kmh: d_think, d_brake, d_stop", eqs="d_stop = u*tr + u**2/(2*b)", tags="braking reaction time road safety",
  steps="During the reaction time the car still moves at u: d = u × tr | While braking, v² = u² − 2bs with v = 0 gives s = u²/2b | Stopping distance is the sum | Doubling speed doubles thinking distance but makes braking distance four times longer",
  ask="d_stop")

X("p9-circular", 9, P, "Motion", "Uniform circular motion", "concept",
  "Constant speed, changing direction: speed from the radius and the time for one round.",
  params="r:Radius of the track:m:50:1:500; T:Time for one round:s:40:1:300",
  out="v:Speed:m/s:2*pi*r/T; circ:Circumference:m:2*pi*r", eqs="v = 2*pi*r/T", tags="circular motion athlete track",
  steps="In one round the object covers the circumference 2πr | It takes time T | Speed = distance/time = 2πr/T")

X("p9-momentum", 9, P, "Force and Laws of Motion", "Momentum", "concept",
  "Momentum p = mv, and why a truck is harder to stop than a bicycle at the same speed.",
  params="m:Mass:kg:1200:0.1:20000; v:Velocity:m/s:15:0:60",
  out="p:Momentum:kg*m/s:m*v", plot="v: p", eqs="p = m*v", tags="momentum mass velocity",
  steps="Momentum is defined as the product of mass and velocity | It is a vector in the direction of the velocity | Its SI unit is kg m/s")

X("p9-newton2", 9, P, "Force and Laws of Motion", "Newton's second law: F = ma", "derivation",
  "Force equals the rate of change of momentum.",
  params="m:Mass:kg:5:0.1:1000; u:Initial velocity:m/s:2:0:50; v:Final velocity:m/s:12:0:50; t:Time:s:4:0.1:60",
  out="a:Acceleration:m/s^2:(v - u)/t; F:Force:N:m*(v - u)/t; dp:Change in momentum:kg*m/s:m*(v - u)",
  eqs="F = m*a | F = (m*v - m*u)/t", tags="newton second law force acceleration momentum",
  steps="Force is proportional to the rate of change of momentum: F ∝ (mv − mu)/t | With SI units the constant is 1: F = m(v − u)/t | Since (v − u)/t = a, F = ma",
  ask="F,a", lab="ramp")

X("p9-catch", 9, P, "Force and Laws of Motion", "Catching a ball: force and time", "concept",
  "Why a fielder pulls the hands back: more time means less force for the same change in momentum.",
  params="m:Mass of ball:kg:0.16:0.05:1; v:Speed of ball:m/s:25:1:45; t:Time to stop:s:0.05:0.005:0.5",
  out="dp:Change in momentum:kg*m/s:m*v; F:Average force:N:m*v/t", plot="t: F", eqs="F = m*v/t",
  tags="impulse cricket ball catch", steps="The ball's momentum falls from mv to 0 | Average force = change in momentum / time | Pulling the hands back increases t, so F falls in proportion",
  ask="F")

X("p9-recoil", 9, P, "Force and Laws of Motion", "Recoil of a gun", "law",
  "Conservation of momentum: the bullet goes forward, the gun comes back.",
  params="m1:Mass of bullet:kg:0.02:0.001:0.1; v1:Muzzle velocity:m/s:400:50:1000; m2:Mass of gun:kg:4:0.5:20",
  out="v2:Recoil velocity:m/s:-m1*v1/m2", eqs="m1*v1 + m2*v2 = 0", tags="conservation of momentum recoil",
  steps="Before firing, gun and bullet are at rest, so total momentum is 0 | After firing, m1v1 + m2v2 must still be 0 | So v2 = −m1v1/m2, backwards and much slower because the gun is heavier",
  ask="v2")

X("p9-stick", 9, P, "Force and Laws of Motion", "Two trolleys that stick together", "practical",
  "Conservation of momentum in a perfectly inelastic collision.",
  params="m1:Mass of trolley A:kg:2:0.1:10; u1:Velocity of A:m/s:3:-10:10; m2:Mass of trolley B:kg:1:0.1:10; u2:Velocity of B:m/s:0:-10:10",
  out="v:Common velocity:m/s:(m1*u1 + m2*u2)/(m1 + m2); p:Total momentum:kg*m/s:m1*u1 + m2*u2; ke_lost:Kinetic energy lost:J:(m1*u1**2 + m2*u2**2)/2 - (m1 + m2)*((m1*u1 + m2*u2)/(m1 + m2))**2/2",
  eqs="m1*u1 + m2*u2 = (m1 + m2)*v", tags="collision momentum conservation inelastic", lab="collisions", ask="v",
  steps="Total momentum before = m1u1 + m2u2 | After sticking, both move with v: momentum (m1 + m2)v | Momentum is conserved, so v = (m1u1 + m2u2)/(m1 + m2) | Some kinetic energy turns into heat and sound")

X("p9-gravitation", 9, P, "Gravitation", "Universal law of gravitation", "law",
  "Every mass attracts every other mass; the force falls with the square of the distance.",
  params="m1:Mass 1:kg:6e24:1:1e30; m2:Mass 2:kg:7.3e22:1:1e30; r:Distance between centres:m:3.84e8:1e3:1e12",
  out="F:Gravitational force:N:G_N*m1*m2/r**2", eqs="F = G*m1*m2/r**2", tags="gravitation force earth moon inverse square",
  steps="The force is proportional to the product of the masses: F ∝ m1m2 | It is inversely proportional to the square of the distance: F ∝ 1/r² | So F = Gm1m2/r², with G = 6.674 × 10⁻¹¹ N m²/kg²",
  lab="orbits", scene="field: q=m1, r=r")

X("p9-g-planet", 9, P, "Gravitation", "Acceleration due to gravity on a planet", "derivation",
  "g = GM/R², worked out for any planet from its mass and radius.",
  params="M_e:Planet mass (Earth masses):-:1:0.01:320; R_e:Planet radius (Earth radii):-:1:0.2:12",
  out="M:Planet mass:kg:M_e*5.972e24; R:Planet radius:m:R_e*6.371e6; g:Surface gravity:m/s^2:G_N*M/R**2",
  eqs="g = G*M/R**2", tags="acceleration due to gravity planet mass radius",
  steps="The weight of a body of mass m is the gravitational force on it: mg = GMm/R² | Cancel m: g = GM/R² | For Earth this gives about 9.8 m/s²",
  ask="g")

X("p9-freefall", 9, P, "Gravitation", "Free fall", "concept",
  "A dropped stone: speed and distance fallen against time.",
  params="g:Acceleration due to gravity:m/s^2:9.8:1:25; t:Time:s:3:0:10",
  out="v:Speed:m/s:g*t; h:Distance fallen:m:g*t**2/2", plot="t: v, h", eqs="v = g*t | h = g*t**2/2",
  tags="free fall gravity drop stone", steps="In free fall the acceleration is g | Put u = 0, a = g into v = u + at: v = gt | And into s = ut + ½at²: h = ½gt²",
  ask="v,h")

X("p9-weight", 9, P, "Gravitation", "Mass and weight", "concept",
  "Mass stays the same everywhere; weight depends on g.",
  params="m:Mass:kg:60:1:500; g:Acceleration due to gravity:m/s^2:9.8:1:25",
  out="W:Weight:N:m*g; W_moon:Weight on the Moon:N:m*1.62; ratio:Weight on the Moon as a fraction:-:1.62/g",
  eqs="W = m*g", tags="weight mass moon", steps="Weight is the force of gravity on a body: W = mg | The Moon's g is about 1.62 m/s², close to one sixth of Earth's",
  ask="W")

X("p9-pressure", 9, P, "Gravitation", "Thrust and pressure", "concept",
  "The same force spread over a larger area gives less pressure.",
  params="F:Thrust:N:600:1:10000; A:Area:m^2:0.05:0.0001:5",
  out="Pr:Pressure:Pa:F/A", plot="A: Pr", eqs="Pr = F/A", tags="pressure thrust area pascal",
  steps="Pressure is thrust per unit area | 1 pascal is 1 N/m² | Halving the area doubles the pressure")

X("p9-archimedes", 9, P, "Gravitation", "Archimedes' principle", "practical",
  "The loss of weight of a body in water equals the weight of water it displaces.",
  params="W_air:Weight in air:N:5:0.5:50; V:Volume of the body:cm^3:200:10:2000; rho:Density of liquid:kg/m^3:1000:700:13600",
  out="Fb:Buoyant force:N:rho*V*1e-6*9.8; W_liq:Apparent weight:N:W_air - rho*V*1e-6*9.8; rel_d:Relative density of body:-:W_air/(1000*V*1e-6*9.8)",
  eqs="Fb = rho*V*g", tags="buoyancy upthrust floatation relative density", lab="buoyancy", ask="Fb,W_liq",
  steps="A body in a liquid displaces its own volume V of liquid | The buoyant force equals the weight of that liquid: ρVg | The spring balance reads the weight in air minus this force")

X("p9-rel-density", 9, P, "Gravitation", "Density and relative density: will it float?", "concept",
  "A body floats when its density is less than the liquid's.",
  params="m:Mass:g:120:1:2000; V:Volume:cm^3:150:1:2000; rho_l:Density of liquid:g/cm^3:1:0.7:13.6",
  out="rho:Density:g/cm^3:m/V; rd:Relative density:-:m/V; sink:Fraction submerged when floating:-:Min(1, m/(V*rho_l))",
  eqs="rho = m/V", tags="density relative density float sink",
  steps="Density = mass/volume | Relative density = density of substance / density of water, and has no unit | A floating body sinks until it displaces its own weight, so the submerged fraction is ρ/ρ_liquid")

X("p9-work", 9, P, "Work and Energy", "Work done by a force", "concept",
  "Only the part of the force along the motion does work.",
  params="F:Force:N:50:0:1000; s:Displacement:m:10:0:200; th:Angle between force and displacement:deg:30:0:180",
  out="W:Work done:J:F*s*cos(th*pi/180)", plot="th: W", eqs="W = F*s*cos(th)", tags="work force displacement angle joule",
  steps="Work = force × displacement in the direction of the force | The component along the motion is F cos θ | So W = Fs cos θ; it is zero at 90° and negative beyond it",
  scene="vector: A=F, B=s, th=th")

X("p9-ke", 9, P, "Work and Energy", "Kinetic energy: ½mv²", "derivation",
  "The work needed to bring a body from rest to speed v.",
  params="m:Mass:kg:2:0.1:2000; v:Speed:m/s:6:0:50",
  out="KE:Kinetic energy:J:m*v**2/2", plot="v: KE", eqs="KE = m*v**2/2", tags="kinetic energy work",
  steps="A force F accelerates the body from rest over a distance s | From v² = u² + 2as with u = 0: s = v²/2a | Work W = Fs = ma × v²/2a = ½mv² | This work is stored as kinetic energy",
  lab="skate")

X("p9-pe", 9, P, "Work and Energy", "Potential energy: mgh", "derivation",
  "Work done against gravity is stored as potential energy.",
  params="m:Mass:kg:10:0.1:1000; g:Acceleration due to gravity:m/s^2:9.8:1:25; h:Height:m:5:0:100",
  out="PE:Potential energy:J:m*g*h", plot="h: PE", eqs="PE = m*g*h", tags="potential energy height gravity",
  steps="Lifting a body at steady speed needs a force equal to its weight mg | Work = force × distance = mg × h | This work is stored as gravitational potential energy")

X("p9-energy-cons", 9, P, "Work and Energy", "Conservation of energy in a falling ball", "law",
  "Potential energy turns into kinetic energy; the sum stays the same.",
  params="m:Mass:kg:1:0.1:50; H:Starting height:m:20:1:200; h:Present height:m:10:0:200",
  out="PE:Potential energy:J:m*9.8*h; KE:Kinetic energy:J:m*9.8*(H - h); total:Total energy:J:m*9.8*H; v:Speed:m/s:sqrt(2*9.8*(H - h))",
  plot="h: PE, KE, total", eqs="m*g*H = m*g*h + m*v**2/2", tags="conservation of energy falling mechanical",
  steps="At the top all energy is potential: mgH | At height h, PE = mgh and the rest is kinetic: KE = mg(H − h) | Their sum is always mgH | Setting ½mv² = mg(H − h) gives v = √(2g(H − h))",
  lab="skate", ask="v,KE")

X("p9-power", 9, P, "Work and Energy", "Power and the commercial unit of energy", "concept",
  "Watts, kilowatt-hours and the electricity bill.",
  params="Pw:Power rating:W:1500:1:5000; hrs:Hours used per day:h:2:0.1:24; days:Days:-:30:1:31:1",
  out="E_kwh:Energy used:kWh:Pw*hrs*days/1000; E_J:Energy used:J:Pw*hrs*days*3600", eqs="E = Pw*t",
  tags="power watt kilowatt hour unit electricity", steps="Power is the rate of doing work: P = W/t | Energy = power × time | 1 kWh = 1000 W × 3600 s = 3.6 × 10⁶ J",
  ask="E_kwh")

X("p9-wave", 9, P, "Sound", "Speed, frequency and wavelength", "law",
  "v = fλ for any wave, including sound.",
  params="f:Frequency:Hz:440:20:20000; v:Speed of sound:m/s:343:200:6000",
  out="lam:Wavelength:m:v/f; T:Time period:s:1/f", plot="f: lam", eqs="v = f*lam | T = 1/f",
  tags="sound wave frequency wavelength speed", scene="wave: lam=lam, f=f",
  steps="In one period T, the wave moves forward one wavelength λ | So speed v = λ/T | Since f = 1/T, v = fλ", lab="waves", ask="lam")

X("p9-echo", 9, P, "Sound", "Echo and SONAR", "practical",
  "Distance to a wall or the sea bed from the time an echo takes to return.",
  params="t:Time for the echo:s:2:0.05:20; v:Speed of sound:m/s:343:300:1600",
  out="d:Distance to the reflector:m:v*t/2", plot="t: d", eqs="d = v*t/2", tags="echo sonar reflection of sound depth",
  steps="Sound goes to the reflector and back, a total distance 2d | 2d = v × t | So d = vt/2 | An echo is heard distinctly only if the wall is at least about 17 m away (0.1 s round trip in air)",
  ask="d")

X("p9-sound-temp", 9, P, "Sound", "Speed of sound and temperature", "concept",
  "Sound travels faster in warm air.",
  params="Tc:Air temperature:degC:25:-20:50",
  out="v:Speed of sound:m/s:331.3*sqrt(1 + Tc/273.15)", plot="Tc: v", eqs="v = 331.3*sqrt(1 + Tc/273.15)",
  tags="speed of sound temperature air", steps="For an ideal gas the speed of sound is proportional to √T (T in kelvin) | At 0 °C it is 331.3 m/s | So v = 331.3 √(T/273.15)")

# ================================================================ Class 10
X("p10-concave-mirror", 10, P, "Light: Reflection and Refraction", "Image by a concave mirror", "practical",
  "Mirror formula and magnification with the New Cartesian sign convention.",
  params="do:Object distance:cm:30:2:100; f_m:Focal length:cm:15:5:50",
  out="u:Object position u:cm:-do; f:Focal length f:cm:-f_m; v:Image position v:cm:1/(1/f - 1/u); m:Magnification:-:-v/u",
  plot="do: v", eqs="1/v + 1/u = 1/f | m = -v/u", scene="mirror: u=do, f=f_m, v=v, m=m, kind=concave",
  tags="mirror formula concave focal length image magnification", lab="lenses", ask="v,m",
  steps="Measure all distances from the pole; distances in front of the mirror are negative | For a concave mirror f is negative and u is negative | The mirror formula gives 1/v = 1/f − 1/u | Magnification m = −v/u; a negative m means a real, inverted image")

X("p10-convex-mirror", 10, P, "Light: Reflection and Refraction", "Image by a convex mirror", "concept",
  "Always virtual, erect and smaller: why it is used as a rear-view mirror.",
  params="do:Object distance:cm:30:2:200; f_m:Focal length:cm:20:5:60",
  out="u:Object position u:cm:-do; f:Focal length f:cm:f_m; v:Image position v:cm:1/(1/f - 1/u); m:Magnification:-:-v/u",
  plot="do: v, m", eqs="1/v + 1/u = 1/f | m = -v/u", scene="mirror: u=do, f=f_m, v=v, m=m, kind=convex",
  tags="convex mirror rear view virtual image", ask="v,m",
  steps="For a convex mirror f is positive and u is negative | 1/v = 1/f − 1/u is always positive, so the image is behind the mirror | m = −v/u lies between 0 and 1: erect and smaller")

X("p10-convex-lens", 10, P, "Light: Reflection and Refraction", "Image by a convex lens", "practical",
  "Lens formula 1/v − 1/u = 1/f and where the image forms.",
  params="do:Object distance:cm:30:2:100; f_l:Focal length:cm:10:3:50",
  out="u:Object position u:cm:-do; f:Focal length f:cm:f_l; v:Image position v:cm:1/(1/f + 1/u); m:Magnification:-:v/u",
  plot="do: v", eqs="1/v - 1/u = 1/f | m = v/u", scene="lens: u=do, f=f_l, v=v, m=m, kind=convex",
  tags="lens formula convex lens focal length image", lab="lenses", ask="v,m",
  steps="Distances are measured from the optical centre; the object is on the left so u is negative | For a convex lens f is positive | The lens formula gives 1/v = 1/f + 1/u | Magnification m = v/u; negative means real and inverted")

X("p10-concave-lens", 10, P, "Light: Reflection and Refraction", "Image by a concave lens", "concept",
  "A diverging lens always gives a virtual, erect, smaller image.",
  params="do:Object distance:cm:30:2:100; f_l:Focal length:cm:15:3:50",
  out="u:Object position u:cm:-do; f:Focal length f:cm:-f_l; v:Image position v:cm:1/(1/f + 1/u); m:Magnification:-:v/u",
  plot="do: v, m", eqs="1/v - 1/u = 1/f", scene="lens: u=do, f=-f_l, v=v, m=m, kind=concave",
  tags="concave lens diverging virtual image", ask="v,m",
  steps="For a concave lens f is negative | 1/v = 1/f + 1/u is negative, so the image is on the same side as the object | m = v/u is between 0 and 1")

X("p10-lens-power", 10, P, "Light: Reflection and Refraction", "Power of a lens and lens combinations", "concept",
  "Dioptres, and why powers add for lenses in contact.",
  params="f1:Focal length of lens 1:cm:25:-100:100; f2:Focal length of lens 2:cm:-50:-100:100",
  out="P1:Power of lens 1:D:100/f1; P2:Power of lens 2:D:100/f2; Pt:Combined power:D:100/f1 + 100/f2; ft:Combined focal length:cm:1/(1/f1 + 1/f2)",
  eqs="P = 1/f | Pt = P1 + P2", tags="power of lens dioptre combination",
  steps="Power is the reciprocal of focal length in metres: P = 1/f | With f in cm, P = 100/f dioptres | For thin lenses in contact the powers add: P = P1 + P2", ask="Pt")

X("p10-snell", 10, P, "Light: Reflection and Refraction", "Refraction: Snell's law", "law",
  "Light bends towards the normal entering a denser medium.",
  params="n1:Refractive index of medium 1:-:1:1:2.5; n2:Refractive index of medium 2:-:1.5:1:2.5; i:Angle of incidence:deg:40:0:89",
  out="r:Angle of refraction:deg:asin(n1*sin(i*pi/180)/n2)*180/pi; dev:Deviation:deg:i - asin(n1*sin(i*pi/180)/n2)*180/pi",
  plot="i: r", eqs="n1*sin(i) = n2*sin(r)", tags="refraction snell law refractive index bending",
  steps="The ratio sin i / sin r is constant for a pair of media | This constant is the refractive index of medium 2 relative to medium 1: n2/n1 | So n1 sin i = n2 sin r", lab="refraction", ask="r")

X("p10-index-speed", 10, P, "Light: Reflection and Refraction", "Refractive index and the speed of light", "concept",
  "Light slows down in glass and water.",
  params="n:Refractive index:-:1.5:1:2.42",
  out="v:Speed of light in the medium:m/s:c0/n", eqs="n = c/v", tags="refractive index speed of light medium",
  steps="Absolute refractive index = speed of light in vacuum / speed in the medium | So v = c/n | Diamond (n = 2.42) slows light to about 1.24 × 10⁸ m/s")

X("p10-slab", 10, P, "Light: Reflection and Refraction", "Refraction through a glass slab", "practical",
  "The emergent ray is parallel to the incident ray but shifted sideways.",
  params="i:Angle of incidence:deg:45:0:85; n:Refractive index of glass:-:1.5:1.3:1.9; t:Slab thickness:cm:5:1:15",
  out="r:Angle of refraction:deg:asin(sin(i*pi/180)/n)*180/pi; e:Angle of emergence:deg:i; d:Lateral displacement:cm:t*sin((i - asin(sin(i*pi/180)/n)*180/pi)*pi/180)/cos(asin(sin(i*pi/180)/n))",
  plot="i: d", eqs="sin(i) = n*sin(r) | d = t*sin(i - r)/cos(r)", tags="glass slab lateral shift emergent ray practical", ask="d,r",
  steps="At the first face sin i = n sin r | At the second face the ray leaves at the same angle i, so it is parallel to the incident ray | Inside the slab the ray travels t/cos r | The sideways shift is that length times sin(i − r)")

X("p10-prism", 10, P, "Light: Reflection and Refraction", "Path of a ray through a prism", "practical",
  "Angle of deviation for a triangular glass prism.",
  params="i:Angle of incidence:deg:45:25:85; A:Angle of the prism:deg:60:30:70; n:Refractive index:-:1.5:1.3:1.9",
  out="r1:Refraction angle at face 1:deg:asin(sin(i*pi/180)/n)*180/pi; r2:Incidence angle at face 2:deg:A - asin(sin(i*pi/180)/n)*180/pi; e:Angle of emergence:deg:asin(n*sin((A - asin(sin(i*pi/180)/n)*180/pi)*pi/180))*180/pi; delta:Angle of deviation:deg:i + asin(n*sin((A - asin(sin(i*pi/180)/n)*180/pi)*pi/180))*180/pi - A",
  plot="i: delta", eqs="r1 + r2 = A | delta = i + e - A", scene="prism: A=A, i=i, e=e, delta=delta, r1=r1",
  tags="prism deviation emergence dispersion practical", ask="delta,e",
  steps="At the first face sin i = n sin r1 | The prism geometry gives r1 + r2 = A | At the second face n sin r2 = sin e | The total deviation is δ = i + e − A; plotting δ against i shows a minimum")

X("p10-myopia", 10, P, "The Human Eye and the Colourful World", "Correcting short and long sight", "concept",
  "The lens power a person needs, from the far point or near point.",
  params="far:Far point of the eye:m:2:0.2:10; near:Near point of the eye:m:1:0.25:3",
  out="P_myopia:Lens for myopia:D:-1/far; P_hyper:Lens for hypermetropia:D:1/0.25 - 1/near",
  eqs="P = -1/far", tags="myopia hypermetropia eye defect spectacles power",
  steps="Myopia: a concave lens must image objects at infinity at the far point, so f = −far point | Power P = 1/f = −1/far point | Hypermetropia: a convex lens must image an object at 25 cm at the near point | 1/f = 1/0.25 − 1/near point")

X("p10-ohm", 10, P, "Electricity", "Ohm's law", "practical",
  "Current through a resistor rises in a straight line with the potential difference.",
  params="V:Potential difference:V:6:0:24; R:Resistance:ohm:12:1:200",
  out="I:Current:A:V/R; Pw:Power:W:V**2/R", plot="V: I", eqs="V = I*R", scene="circuit: V=V, I=I, R=R, layout=single",
  tags="ohm law current voltage resistance practical graph", lab="circuit", ask="I",
  steps="Keep the temperature of the conductor constant | Vary V with a rheostat and read I on the ammeter | The V-I graph is a straight line through the origin | Its slope V/I is the resistance R")

X("p10-resistivity", 10, P, "Electricity", "Resistance of a wire", "concept",
  "Longer wires resist more, thicker wires less: R = ρL/A.",
  params="rho:Resistivity:ohm*m:1.7e-8:1e-8:1.1e-6; L:Length:m:10:0.1:100; dmm:Diameter:mm:0.5:0.1:5",
  out="A:Cross-section area:m^2:pi*(dmm/1000)**2/4; R:Resistance:ohm:rho*L/(pi*(dmm/1000)**2/4)",
  plot="L: R", eqs="R = rho*L/A", tags="resistivity length area wire copper nichrome", ask="R",
  steps="R is proportional to length L and inversely proportional to area A | The constant is the resistivity ρ of the material | A = πd²/4 for a round wire")

X("p10-series", 10, P, "Electricity", "Resistors in series", "practical",
  "The same current flows through each resistor and the voltages add.",
  params="V:Battery voltage:V:12:1:24; R1:R1:ohm:4:1:100; R2:R2:ohm:6:1:100; R3:R3:ohm:10:1:100",
  out="Rs:Equivalent resistance:ohm:R1 + R2 + R3; I:Current:A:V/(R1 + R2 + R3); V1:Voltage across R1:V:V*R1/(R1 + R2 + R3); V2:Voltage across R2:V:V*R2/(R1 + R2 + R3); V3:Voltage across R3:V:V*R3/(R1 + R2 + R3)",
  eqs="Rs = R1 + R2 + R3", scene="circuit: V=V, I=I, R=Rs, layout=series",
  tags="series combination resistors equivalent", lab="circuit", ask="Rs,I",
  steps="The same current I flows through every resistor | The battery voltage is shared: V = V1 + V2 + V3 | Each V = IR, so V = I(R1 + R2 + R3) | So Rs = R1 + R2 + R3")

X("p10-parallel", 10, P, "Electricity", "Resistors in parallel", "practical",
  "Each branch has the full voltage and the currents add.",
  params="V:Battery voltage:V:12:1:24; R1:R1:ohm:4:1:100; R2:R2:ohm:6:1:100; R3:R3:ohm:12:1:100",
  out="Rp:Equivalent resistance:ohm:1/(1/R1 + 1/R2 + 1/R3); I:Total current:A:V/R1 + V/R2 + V/R3; I1:Current in R1:A:V/R1; I2:Current in R2:A:V/R2; I3:Current in R3:A:V/R3",
  eqs="1/Rp = 1/R1 + 1/R2 + 1/R3", scene="circuit: V=V, I=I, R=Rp, layout=parallel",
  tags="parallel combination resistors household wiring", lab="circuit", ask="Rp,I",
  steps="Every branch is connected across the same V | The branch currents add: I = I1 + I2 + I3 | Each I = V/R, so V/Rp = V/R1 + V/R2 + V/R3 | Cancel V: 1/Rp = 1/R1 + 1/R2 + 1/R3")

X("p10-joule-heating", 10, P, "Electricity", "Heating effect of current", "law",
  "Joule's law H = I²Rt.",
  params="I:Current:A:2:0:20; R:Resistance:ohm:50:1:500; t:Time:s:60:1:3600",
  out="H:Heat produced:J:I**2*R*t; Pw:Power:W:I**2*R; V:Voltage:V:I*R", plot="I: H", eqs="H = I**2*R*t | Pw = V*I",
  tags="joule heating effect heater fuse power", steps="Work done moving charge Q through voltage V is VQ | Q = It, so W = VIt | With V = IR, H = I²Rt", ask="H")

X("p10-wire-field", 10, P, "Magnetic Effects of Electric Current", "Magnetic field of a straight wire", "concept",
  "Field lines are circles; the field falls off as 1/r.",
  params="I:Current:A:10:0.1:100; r:Distance from the wire:cm:2:0.1:50",
  out="B:Magnetic field:T:mu0*I/(2*pi*r/100)", plot="r: B", eqs="B = mu0*I/(2*pi*r)",
  tags="magnetic field straight conductor right hand thumb rule",
  steps="Field lines are concentric circles round the wire (right-hand thumb rule) | The field is proportional to I and inversely proportional to r | B = μ₀I/2πr with μ₀ = 4π × 10⁻⁷ T m/A", ask="B")

X("p10-solenoid", 10, P, "Magnetic Effects of Electric Current", "Field inside a solenoid", "concept",
  "A uniform field, like a bar magnet's, from a coil of many turns.",
  params="N_t:Number of turns:-:500:10:5000:10; L:Length of solenoid:cm:20:2:100; I:Current:A:2:0.1:20",
  out="n:Turns per metre:1/m:N_t/(L/100); B:Magnetic field inside:T:mu0*N_t/(L/100)*I", plot="I: B", eqs="B = mu0*n*I",
  tags="solenoid electromagnet magnetic field coil", ask="B",
  steps="Inside a long solenoid the field is uniform and along the axis | It is proportional to the turns per unit length n and the current I | B = μ₀nI")

X("p10-force-wire", 10, P, "Magnetic Effects of Electric Current", "Force on a current in a magnetic field", "law",
  "Fleming's left-hand rule and F = BIL sin θ.",
  params="B:Magnetic field:T:0.5:0.01:2; I:Current:A:5:0:50; L:Length of wire:m:0.2:0.01:2; th:Angle to the field:deg:90:0:180",
  out="F:Force:N:B*I*L*sin(th*pi/180)", plot="th: F", eqs="F = B*I*L*sin(th)", tags="fleming left hand rule motor force",
  steps="The force is largest when the wire is at right angles to the field | It is proportional to B, I and L | F = BIL sin θ, directed by Fleming's left-hand rule", ask="F")

X("p10-lever", 10, P, "Machines", "Levers and mechanical advantage", "law",
  "Principle of moments for a lever.", boards=ICSE,
  params="L:Load:N:600:10:5000; la:Load arm:m:0.2:0.05:3; ea:Effort arm:m:1.2:0.05:3",
  out="E:Effort needed:N:L*la/ea; MA:Mechanical advantage:-:ea/la", eqs="L*la = E*ea | MA = L/E",
  scene="lever: la=la, ea=ea, L=L, E=E", tags="lever principle of moments mechanical advantage machine", ask="E,MA",
  steps="In balance the clockwise and anticlockwise moments are equal | Load × load arm = effort × effort arm | MA = load/effort = effort arm/load arm")

X("p10-pulley", 10, P, "Machines", "Block and tackle pulley system", "law",
  "More ropes supporting the load means less effort, but more rope to pull.", boards=ICSE,
  params="n:Number of pulleys:-:4:1:8:1; L:Load:N:800:10:5000; eta:Efficiency:%:80:30:100",
  out="MA:Mechanical advantage:-:n*eta/100; VR:Velocity ratio:-:n; E:Effort:N:L/(n*eta/100)",
  eqs="VR = n | eta = MA/VR", tags="pulley block tackle velocity ratio efficiency machine", ask="E,MA",
  steps="With n pulleys the load is held by n strands, so the effort moves n times as far: VR = n | Efficiency η = output work / input work = MA/VR | So MA = ηn and effort = load/MA")

X("p10-calorimetry", 10, P, "Calorimetry", "Mixing hot and cold water", "practical",
  "Principle of calorimetry: heat lost equals heat gained.", boards=ICSE,
  params="m1:Mass of hot water:g:200:10:1000; T1:Temperature of hot water:degC:80:0:100; m2:Mass of cold water:g:300:10:1000; T2:Temperature of cold water:degC:20:0:100",
  out="Tf:Final temperature:degC:(m1*T1 + m2*T2)/(m1 + m2); Q:Heat exchanged:J:m1*4.186*(T1 - (m1*T1 + m2*T2)/(m1 + m2))",
  eqs="m1*c*(T1 - Tf) = m2*c*(Tf - T2)", tags="calorimetry mixture specific heat capacity", ask="Tf",
  steps="Heat lost by hot water = m1c(T1 − Tf) | Heat gained by cold water = m2c(Tf − T2) | With no heat lost to the surroundings these are equal | Solve for Tf = (m1T1 + m2T2)/(m1 + m2)")

X("p10-latent", 10, P, "Calorimetry", "Melting ice: latent heat", "concept",
  "Heat to melt ice at 0 °C and then warm the water.", boards=ICSE,
  params="m:Mass of ice:g:100:1:2000; Tf:Final water temperature:degC:30:0:100",
  out="Q_melt:Heat to melt:J:m*334; Q_warm:Heat to warm the water:J:m*4.186*Tf; Q:Total heat:J:m*334 + m*4.186*Tf",
  eqs="Q = m*L + m*c*Tf", tags="latent heat of fusion ice melting", ask="Q",
  steps="Melting at 0 °C takes latent heat: Q = mL with L = 334 J/g | Warming the water takes mcΔT with c = 4.186 J/g °C | Add the two")

X("p10-half-life", 10, P, "Radioactivity", "Half-life", "concept",
  "After every half-life, half of the remaining nuclei decay.", boards=ICSE,
  params="N0:Starting nuclei:-:10000:100:1000000; T_half:Half-life:days:8:0.1:1000; t:Time elapsed:days:24:0:5000",
  out="N_left:Nuclei left:-:N0*(1/2)**(t/T_half); frac:Fraction left:-:(1/2)**(t/T_half); halves:Half-lives passed:-:t/T_half",
  series="Nt:Nuclei left:-:N0*(1/2)**(tt/T_half)", plot="tt=0..6*T_half: Nt", eqs="N_left = N0*(1/2)**(t/T_half)",
  scene="decay: N0=N0, N=N_left, half=T_half", tags="radioactivity half life decay", lab="decay", ask="N_left",
  steps="In each half-life the number of undecayed nuclei halves | After n half-lives N = N0 (½)ⁿ | n = t/T½")

# ================================================================ Class 11
X("p11-errors", 11, P, "Units and Measurements", "Combining errors in measurement", "concept",
  "Percentage error in a quantity worked out from powers of measured quantities.",
  params="ea:Percentage error in A:%:1:0:10; pa:Power of A:-:2:-3:3:1; eb:Percentage error in B:%:2:0:10; pb:Power of B:-:-1:-3:3:1",
  out="ez:Percentage error in Z:%:Abs(pa)*ea + Abs(pb)*eb", eqs="ez = Abs(pa)*ea + Abs(pb)*eb",
  tags="error analysis percentage error significant figures measurement",
  steps="For Z = Aᵃ Bᵇ take logs: ln Z = a ln A + b ln B | Differentiate: ΔZ/Z = a ΔA/A + b ΔB/B | Errors always add, so use the magnitudes of the powers")

X("p11-motion-graphs", 11, P, "Motion in a Straight Line", "Position-time and velocity-time graphs", "graph",
  "The slope of x-t is velocity; the slope of v-t is acceleration.",
  params="x0:Starting position:m:0:-50:50; v0:Initial velocity:m/s:10:-20:20; a:Acceleration:m/s^2:-2:-10:10; t:Time:s:4:0:20",
  out="x:Position:m:x0 + v0*t + a*t**2/2; v:Velocity:m/s:v0 + a*t", plot="t: x, v", eqs="x = x0 + v0*t + a*t**2/2 | v = v0 + a*t",
  tags="kinematics graph slope velocity time", scene="path",
  steps="With constant acceleration, velocity is linear in time | Position is the area under the velocity graph, which gives a parabola | Where v crosses zero, the x-t graph has its turning point", ask="x,v")

X("p11-relative", 11, P, "Motion in a Straight Line", "Relative velocity of two trains", "concept",
  "How fast one train closes in on another, and when they meet.",
  params="vA:Velocity of train A:km/h:72:-150:150; vB:Velocity of train B:km/h:-54:-150:150; d:Initial gap:km:5:0.1:100",
  out="vAB:Velocity of A relative to B:km/h:vA - vB; t_meet:Time to meet:min:60*d/(vA - vB)", eqs="vAB = vA - vB",
  tags="relative velocity trains meet", steps="Velocity of A relative to B is vA − vB | The gap closes at this rate | Time = gap / relative speed", ask="t_meet")

X("p11-projectile", 11, P, "Motion in a Plane", "Projectile motion", "derivation",
  "A parabola: horizontal speed stays the same while gravity pulls it down.",
  params="v0:Launch speed:m/s:20:1:60; th:Launch angle:deg:45:1:89; g:Acceleration due to gravity:m/s^2:9.8:1.6:25",
  out="T:Time of flight:s:2*v0*sin(th*pi/180)/g; H:Maximum height:m:(v0*sin(th*pi/180))**2/(2*g); R:Horizontal range:m:v0**2*sin(2*th*pi/180)/g",
  series="x:Horizontal distance:m:v0*cos(th*pi/180)*t; y:Height:m:v0*sin(th*pi/180)*t - g*t**2/2", plot="t=0..T: x ~ y",
  eqs="T = 2*v0*sin(th)/g | H = v0**2*sin(th)**2/(2*g) | R = v0**2*sin(2*th)/g | y = x*tan(th) - g*x**2/(2*v0**2*cos(th)**2)",
  scene="path", tags="projectile range height time of flight parabola trajectory", lab="projectile", ask="R,H,T",
  steps="Split the velocity: ux = v₀cos θ, uy = v₀sin θ | Horizontally there is no acceleration: x = v₀cos θ · t | Vertically a = −g: y = v₀sin θ · t − ½gt² | y = 0 again at T = 2v₀sin θ/g | Range R = ux × T = v₀² sin 2θ / g | Eliminating t gives a parabola")

X("p11-range-angle", 11, P, "Motion in a Plane", "Range against launch angle", "graph",
  "Maximum range at 45°, and complementary angles give the same range.",
  params="v0:Launch speed:m/s:25:1:60; th:Launch angle:deg:30:0:90",
  out="R:Range:m:v0**2*sin(2*th*pi/180)/9.8; R_comp:Range at the complementary angle:m:v0**2*sin(2*(90 - th)*pi/180)/9.8; R_max:Maximum range:m:v0**2/9.8",
  plot="th: R", eqs="R = v0**2*sin(2*th)/g", tags="range maximum 45 degrees complementary angles", lab="projectile",
  steps="R = v₀² sin 2θ / g | sin 2θ is largest (1) at 2θ = 90°, so θ = 45° | sin 2θ = sin(180° − 2θ), so θ and 90° − θ give equal ranges", ask="R")

X("p11-river", 11, P, "Motion in a Plane", "Crossing a river", "concept",
  "Shortest time or shortest path: two ways to cross.",
  params="w:River width:m:200:10:2000; vb:Boat speed in still water:m/s:4:0.5:15; vr:River current:m/s:2:0:10",
  out="t_min:Shortest crossing time:s:w/vb; drift:Drift in that case:m:vr*w/vb; ang:Heading upstream for a straight path:deg:asin(Min(vr/vb, 1))*180/pi; t_straight:Time on the straight path:s:w/sqrt(vb**2 - vr**2)",
  eqs="t_min = w/vb | drift = vr*w/vb", tags="river boat relative velocity drift", scene="vector: A=vb, B=vr, th=90",
  steps="Heading straight across, the across-speed is vb: t = w/vb | The current carries the boat downstream by vr × t | To land opposite, head upstream at sin α = vr/vb; the across-speed becomes √(vb² − vr²)", ask="t_min,drift")

X("p11-centripetal", 11, P, "Motion in a Plane", "Centripetal acceleration", "derivation",
  "Changing direction at constant speed needs an acceleration towards the centre.",
  params="v:Speed:m/s:10:0.1:100; r:Radius:m:20:0.1:500",
  out="ac:Centripetal acceleration:m/s^2:v**2/r; omega:Angular speed:rad/s:v/r; T:Period:s:2*pi*r/v", plot="v: ac", eqs="ac = v**2/r | v = omega*r",
  tags="centripetal acceleration circular motion angular velocity",
  steps="In a short time Δt the velocity turns through Δθ = vΔt/r | The change in velocity has size vΔθ | So a = vΔθ/Δt = v²/r, pointing to the centre", ask="ac")

X("p11-incline", 11, P, "Laws of Motion", "Block on a rough incline", "practical",
  "Gravity along the slope against friction.",
  params="th:Angle of incline:deg:30:0:80; mu:Coefficient of friction:-:0.2:0:1; m:Mass:kg:2:0.1:50",
  out="a:Acceleration down the slope:m/s^2:Max(0, 9.8*(sin(th*pi/180) - mu*cos(th*pi/180))); N:Normal reaction:N:m*9.8*cos(th*pi/180); f:Friction (limiting):N:mu*m*9.8*cos(th*pi/180); th_slip:Angle of repose:deg:atan(mu)*180/pi",
  plot="th: a", eqs="a = g*(sin(th) - mu*cos(th)) | tan(th_slip) = mu", scene="incline: th=th, a=a, mu=mu",
  tags="inclined plane friction normal reaction angle of repose", lab="ramp", ask="a",
  steps="Resolve the weight: mg sin θ along the slope and mg cos θ into it | The normal reaction is N = mg cos θ | Limiting friction is μN | Net force down the slope mg sin θ − μmg cos θ, so a = g(sin θ − μ cos θ) | The block starts to slip when tan θ = μ")

X("p11-banking", 11, P, "Laws of Motion", "Banking of roads", "derivation",
  "The safe speed on a banked curve with friction.",
  params="r:Radius of the curve:m:100:10:1000; th:Banking angle:deg:15:0:40; mu:Coefficient of friction:-:0.3:0:1",
  out="v_opt:Speed with no friction needed:m/s:sqrt(r*9.8*tan(th*pi/180)); v_max:Maximum safe speed:m/s:sqrt(r*9.8*(mu + tan(th*pi/180))/(1 - mu*tan(th*pi/180)))",
  plot="th: v_opt, v_max", eqs="v_opt**2 = r*g*tan(th) | v_max**2 = r*g*(mu + tan(th))/(1 - mu*tan(th))",
  tags="banking of roads curve circular motion friction", ask="v_max",
  steps="Resolve forces on the car: N cos θ = mg + f sin θ and N sin θ + f cos θ = mv²/r | At the limit f = μN | Dividing the two equations gives v² = rg(μ + tan θ)/(1 − μ tan θ) | With μ = 0: v₀² = rg tan θ")

X("p11-atwood", 11, P, "Laws of Motion", "Two masses over a pulley", "derivation",
  "Atwood machine: acceleration and string tension.",
  params="m1:Heavier mass:kg:5:0.1:50; m2:Lighter mass:kg:3:0.1:50",
  out="a:Acceleration:m/s^2:(m1 - m2)*9.8/(m1 + m2); T:Tension:N:2*m1*m2*9.8/(m1 + m2)", eqs="a = (m1 - m2)*g/(m1 + m2) | T = 2*m1*m2*g/(m1 + m2)",
  tags="atwood machine pulley tension", ask="a,T",
  steps="For m1 (going down): m1g − T = m1a | For m2 (going up): T − m2g = m2a | Add them: (m1 − m2)g = (m1 + m2)a | Substitute back for T = 2m1m2g/(m1 + m2)")

X("p11-lift", 11, P, "Laws of Motion", "Apparent weight in a lift", "concept",
  "A weighing scale in an accelerating lift.",
  params="m:Mass of person:kg:60:10:150; a:Lift acceleration (up is positive):m/s^2:2:-9.8:10",
  out="R:Scale reading (force):N:m*(9.8 + a); R_kg:Scale reading:kg:m*(9.8 + a)/9.8", plot="a: R", eqs="R = m*(g + a)",
  tags="apparent weight lift elevator normal reaction weightlessness", ask="R",
  steps="Forces on the person: weight mg down, normal reaction R up | Newton's second law: R − mg = ma | So R = m(g + a); in free fall (a = −g) R = 0")

X("p11-spring-energy", 11, P, "Work, Energy and Power", "Spring potential energy", "derivation",
  "Work done stretching a spring is the area under the force-extension line.",
  params="k:Spring constant:N/m:200:1:5000; x:Extension:m:0.1:0:1",
  out="F:Spring force:N:k*x; U:Stored energy:J:k*x**2/2", plot="x: F, U", eqs="U = k*x**2/2 | F = k*x",
  tags="spring potential energy hooke work", lab="springs", ask="U",
  steps="The spring force grows linearly: F = kx | Work to stretch is the area under the F-x line from 0 to x | That triangle has area ½ × x × kx = ½kx²")

X("p11-elastic", 11, P, "Work, Energy and Power", "Elastic collision in one dimension", "derivation",
  "Both momentum and kinetic energy are conserved.",
  params="m1:Mass 1:kg:2:0.1:20; u1:Velocity of 1:m/s:5:-20:20; m2:Mass 2:kg:1:0.1:20; u2:Velocity of 2:m/s:0:-20:20",
  out="v1:Velocity of 1 after:m/s:((m1 - m2)*u1 + 2*m2*u2)/(m1 + m2); v2:Velocity of 2 after:m/s:((m2 - m1)*u2 + 2*m1*u1)/(m1 + m2)",
  eqs="m1*u1 + m2*u2 = m1*v1 + m2*v2 | v1 = ((m1 - m2)*u1 + 2*m2*u2)/(m1 + m2)", tags="elastic collision momentum kinetic energy",
  lab="collisions", ask="v1,v2",
  steps="Momentum: m1u1 + m2u2 = m1v1 + m2v2 | Kinetic energy: ½m1u1² + ½m2u2² = ½m1v1² + ½m2v2² | Together they give u1 − u2 = v2 − v1 (relative speed reverses) | Solve the two linear equations for v1 and v2")

X("p11-power-motor", 11, P, "Work, Energy and Power", "Power to lift and move", "concept",
  "A motor lifting a load at steady speed.",
  params="m:Mass lifted:kg:500:1:5000; v:Lifting speed:m/s:0.5:0.01:5; eta:Motor efficiency:%:80:10:100",
  out="P_out:Useful power:W:m*9.8*v; P_in:Electrical power needed:W:m*9.8*v/(eta/100)", eqs="P = F*v",
  tags="power force velocity motor lift efficiency", ask="P_in",
  steps="At steady speed the force equals the weight mg | Power = work per second = F × distance per second = Fv | Input power = useful power / efficiency")

X("p11-com", 11, P, "System of Particles and Rotational Motion", "Centre of mass of two particles", "concept",
  "The balance point sits closer to the heavier mass.",
  params="m1:Mass 1:kg:2:0.1:50; x1:Position of 1:m:0:-10:10; m2:Mass 2:kg:6:0.1:50; x2:Position of 2:m:4:-10:10",
  out="xcm:Centre of mass:m:(m1*x1 + m2*x2)/(m1 + m2)", eqs="xcm = (m1*x1 + m2*x2)/(m1 + m2)", tags="centre of mass balance",
  steps="The centre of mass is the mass-weighted average of positions | x_cm = (m1x1 + m2x2)/(m1 + m2)")

X("p11-torque", 11, P, "System of Particles and Rotational Motion", "Torque", "concept",
  "Turning effect of a force: bigger with a longer spanner.",
  params="F:Force:N:50:0:500; r:Distance from the axis:m:0.3:0.01:2; th:Angle between r and F:deg:90:0:180",
  out="tau:Torque:N*m:r*F*sin(th*pi/180)", plot="th: tau", eqs="tau = r*F*sin(th)", tags="torque moment of force spanner",
  steps="Torque is the moment of a force about an axis | Only the part of F perpendicular to r turns the body: F sin θ | τ = rF sin θ", ask="tau")

X("p11-rolling", 11, P, "System of Particles and Rotational Motion", "Rolling down an incline", "derivation",
  "Ring, disc or sphere: which reaches the bottom first?",
  params="kk:Shape factor I/(MR²) (ring 1, disc 0.5, sphere 0.4):-:0.5:0:1; th:Angle of incline:deg:30:1:80; L:Length of incline:m:5:0.5:50",
  out="a:Acceleration:m/s^2:9.8*sin(th*pi/180)/(1 + kk); t:Time to the bottom:s:sqrt(2*L*(1 + kk)/(9.8*sin(th*pi/180))); v:Speed at the bottom:m/s:sqrt(2*9.8*L*sin(th*pi/180)/(1 + kk))",
  plot="kk: t", eqs="a = g*sin(th)/(1 + kk)", tags="rolling moment of inertia ring disc sphere incline", lab="rolling", ask="a,v",
  steps="Energy at the bottom is shared: mgh = ½mv² + ½Iω² | For rolling without slipping ω = v/R, and I = kMR² | So mgh = ½mv²(1 + k) | Bodies with smaller k (sphere) reach the bottom first")

X("p11-skater", 11, P, "System of Particles and Rotational Motion", "Conservation of angular momentum", "law",
  "A skater spins faster by pulling the arms in.",
  params="I1:Moment of inertia, arms out:kg*m^2:4:0.5:20; w1:Spin rate, arms out:rev/s:1:0.1:5; I2:Moment of inertia, arms in:kg*m^2:1.5:0.2:20",
  out="w2:Spin rate, arms in:rev/s:I1*w1/I2; KE_ratio:Kinetic energy ratio (after/before):-:I1/I2", eqs="I1*w1 = I2*w2",
  tags="angular momentum conservation skater moment of inertia", ask="w2",
  steps="With no external torque, angular momentum L = Iω stays constant | I1ω1 = I2ω2 | Smaller I means larger ω; kinetic energy rises because the skater does work pulling in")

X("p11-orbit", 11, P, "Gravitation", "Satellite orbits: speed and period", "derivation",
  "Orbital speed and period of a satellite at any height above Earth.",
  params="h:Height above the surface:km:400:100:36000",
  out="r:Orbit radius:m:6.371e6 + h*1000; v:Orbital speed:m/s:sqrt(G_N*5.972e24/(6.371e6 + h*1000)); T:Period:min:2*pi*sqrt((6.371e6 + h*1000)**3/(G_N*5.972e24))/60",
  plot="h: v", eqs="v = sqrt(G*M/r) | T = 2*pi*sqrt(r**3/(G*M))", tags="satellite orbital velocity period geostationary", lab="orbits", ask="v,T",
  steps="Gravity supplies the centripetal force: GMm/r² = mv²/r | So v = √(GM/r) | Period T = 2πr/v = 2π√(r³/GM) | At about 35,800 km height T is one day: a geostationary orbit")

X("p11-escape", 11, P, "Gravitation", "Escape speed", "derivation",
  "The launch speed needed to never come back.",
  params="M_e:Planet mass (Earth masses):-:1:0.01:320; R_e:Planet radius (Earth radii):-:1:0.2:12",
  out="ve:Escape speed:km/s:sqrt(2*G_N*M_e*5.972e24/(R_e*6.371e6))/1000; vo:Speed for a low orbit:km/s:sqrt(G_N*M_e*5.972e24/(R_e*6.371e6))/1000",
  eqs="ve = sqrt(2*G*M/R)", tags="escape velocity planet", ask="ve",
  steps="To escape, kinetic energy must at least cancel the gravitational potential energy: ½mv² = GMm/R | So vₑ = √(2GM/R) | This is √2 times the low-orbit speed")

X("p11-g-height", 11, P, "Gravitation", "Variation of g with height and depth", "derivation",
  "g falls as you climb and as you dig.",
  params="h:Height or depth:km:500:0:6371",
  out="g_h:g at height h:m/s^2:9.8*(6371/(6371 + h))**2; g_d:g at depth h:m/s^2:9.8*(1 - h/6371)", plot="h: g_h, g_d",
  eqs="g_h = g*(R/(R + h))**2 | g_d = g*(1 - h/R)", tags="acceleration due to gravity height depth",
  steps="At height h, g = GM/(R + h)² = g(R/(R + h))² | At depth d only the mass inside radius R − d attracts | For uniform density that mass scales as (R − d)³, giving g_d = g(1 − d/R)")

X("p11-kepler", 11, P, "Gravitation", "Kepler's third law", "law",
  "T² ∝ a³ for every planet round the Sun.",
  params="a:Semi-major axis:AU:1.52:0.3:40",
  out="T:Orbital period:years:a**1.5; v:Mean orbital speed:km/s:29.78/sqrt(a)", plot="a: T", eqs="T**2 = a**3",
  tags="kepler third law planet period", lab="kepler",
  steps="For a circular orbit GMm/a² = m(2π/T)²a | So T² = 4π²a³/GM | In years and AU for the Sun this becomes T² = a³")

X("p11-young", 11, P, "Mechanical Properties of Solids", "Young's modulus: stretching a wire", "practical",
  "Searle's method: extension of a wire under load.",
  params="Mk:Load:kg:5:0.1:20; L:Length of wire:m:2:0.5:5; dmm:Diameter:mm:0.5:0.1:2; Yg:Young's modulus:GPa:200:50:400",
  out="stress:Stress:Pa:Mk*9.8/(pi*(dmm/1000)**2/4); strain:Strain:-:Mk*9.8/(pi*(dmm/1000)**2/4)/(Yg*1e9); dL:Extension:mm:1000*L*Mk*9.8/(pi*(dmm/1000)**2/4)/(Yg*1e9)",
  plot="Mk: dL", eqs="Yg = (F/A)/(dL/L)", tags="young modulus stress strain elasticity searle", ask="dL",
  steps="Stress = F/A and strain = ΔL/L | Within the elastic limit stress/strain = Y | So ΔL = FL/(AY); plotting load against extension gives a straight line")

X("p11-hooke", 11, P, "Mechanical Properties of Solids", "Spring constant by Hooke's law", "practical",
  "Load against extension for a spring.",
  params="k:Spring constant:N/m:40:1:500; Mg:Load:g:200:0:1000",
  out="F:Force:N:Mg/1000*9.8; x:Extension:cm:100*Mg/1000*9.8/k", plot="Mg: x", eqs="F = k*x",
  tags="hooke law spring constant extension load practical", lab="springs", ask="x",
  steps="Hang known masses and measure the extension | Within the elastic limit F = kx | The slope of the force-extension graph is k")

X("p11-hydraulic", 11, P, "Mechanical Properties of Fluids", "Hydraulic lift", "law",
  "Pascal's law: a small force on a small piston lifts a car.",
  params="F1:Force on small piston:N:200:1:2000; d1:Small piston diameter:cm:4:1:50; d2:Large piston diameter:cm:40:5:200",
  out="F2:Force on large piston:N:F1*(d2/d1)**2; P:Pressure:Pa:F1/(pi*(d1/100)**2/4)", eqs="F1/A1 = F2/A2",
  tags="pascal law hydraulic lift brake press", ask="F2",
  steps="Pressure applied to an enclosed liquid is passed on equally everywhere | F1/A1 = F2/A2 | So F2 = F1 × A2/A1 = F1 (d2/d1)²")

X("p11-pressure-depth", 11, P, "Mechanical Properties of Fluids", "Pressure at a depth", "derivation",
  "Pressure grows linearly with depth in a liquid.",
  params="h:Depth:m:10:0:100; rho:Density of liquid:kg/m^3:1000:700:13600",
  out="Pg:Gauge pressure:Pa:rho*9.8*h; Pabs:Absolute pressure:Pa:101325 + rho*9.8*h", plot="h: Pabs", eqs="P = P0 + rho*g*h",
  tags="pressure depth liquid gauge absolute", ask="Pabs",
  steps="Take a column of liquid of area A and height h | Its weight ρAhg is held up by the extra pressure on its base | So P − P₀ = ρgh")

X("p11-venturi", 11, P, "Mechanical Properties of Fluids", "Bernoulli: flow through a narrow pipe", "law",
  "The fluid speeds up where the pipe narrows and its pressure drops.",
  params="v1:Speed in wide section:m/s:2:0.1:10; A_ratio:Area ratio A1/A2:-:3:1:10; rho:Fluid density:kg/m^3:1000:1:1500",
  out="v2:Speed in narrow section:m/s:v1*A_ratio; dP:Pressure drop:Pa:rho*((v1*A_ratio)**2 - v1**2)/2",
  plot="A_ratio: dP", eqs="A1*v1 = A2*v2 | P1 + rho*v1**2/2 = P2 + rho*v2**2/2", tags="bernoulli venturi continuity",
  lab="bernoulli", ask="v2,dP",
  steps="Continuity: the same volume passes each second, so A1v1 = A2v2 | Bernoulli along a streamline: P + ½ρv² is constant | So P1 − P2 = ½ρ(v2² − v1²)")

X("p11-stokes", 11, P, "Mechanical Properties of Fluids", "Terminal velocity: Stokes' law", "practical",
  "A steel ball falling through glycerine reaches a steady speed.",
  params="r:Radius of ball:mm:1:0.1:5; rho:Density of ball:kg/m^3:7800:1000:12000; sig:Density of liquid:kg/m^3:1260:700:1500; eta:Viscosity:Pa*s:1.4:0.001:5",
  out="vt:Terminal velocity:m/s:2*(r/1000)**2*(rho - sig)*9.8/(9*eta)", plot="r: vt", eqs="vt = 2*r**2*(rho - sig)*g/(9*eta)",
  tags="stokes law terminal velocity viscosity", ask="vt",
  steps="Viscous drag on a sphere is 6πηrv (Stokes' law) | At terminal speed: weight = buoyancy + drag | (4/3)πr³ρg = (4/3)πr³σg + 6πηrv | So v = 2r²(ρ − σ)g/9η")

X("p11-capillary", 11, P, "Mechanical Properties of Fluids", "Capillary rise", "practical",
  "Water climbs higher in a narrower tube.",
  params="rmm:Tube radius:mm:0.5:0.05:3; T:Surface tension:N/m:0.072:0.02:0.5; th:Contact angle:deg:0:0:89; rho:Density:kg/m^3:1000:700:1500",
  out="h:Rise:cm:100*2*T*cos(th*pi/180)/((rmm/1000)*rho*9.8)", plot="rmm: h", eqs="h = 2*T*cos(th)/(r*rho*g)",
  tags="capillary rise surface tension", ask="h",
  steps="Surface tension pulls up round the rim: 2πrT cos θ | It holds up a column of weight πr²hρg | Equate: h = 2T cos θ / (rρg)")

X("p11-expansion", 11, P, "Thermal Properties of Matter", "Thermal expansion of a rod", "concept",
  "Why railway tracks have gaps.",
  params="L:Length:m:12:0.1:100; alpha:Coefficient of linear expansion:1/K:1.2e-5:1e-6:3e-5; dT:Temperature rise:K:40:0:200",
  out="dL:Expansion:mm:1000*alpha*L*dT; beta:Volume coefficient:1/K:3*alpha", plot="dT: dL", eqs="dL = alpha*L*dT",
  tags="thermal expansion linear coefficient rail gap", ask="dL",
  steps="For small ΔT the change in length is proportional to L and ΔT | ΔL = αLΔT | Area and volume coefficients are about 2α and 3α")

X("p11-cooling", 11, P, "Thermal Properties of Matter", "Newton's law of cooling", "practical",
  "A cup of tea cools fast at first, then slowly.",
  params="T0:Starting temperature:degC:90:30:100; Ts:Room temperature:degC:25:0:40; k:Cooling constant:1/min:0.05:0.005:0.5; t:Time:min:10:0:120",
  out="T:Temperature:degC:Ts + (T0 - Ts)*exp(-k*t); rate:Cooling rate:degC/min:k*(Ts + (T0 - Ts)*exp(-k*t) - Ts)",
  plot="t: T", eqs="T = Ts + (T0 - Ts)*exp(-k*t)", tags="newton law of cooling temperature time practical", ask="T",
  steps="The rate of cooling is proportional to the temperature excess: dT/dt = −k(T − Ts) | Separate variables and integrate | T − Ts = (T₀ − Ts)e^(−kt)")

X("p11-specific-heat", 11, P, "Thermal Properties of Matter", "Specific heat capacity", "law",
  "Heat needed to warm a body: Q = mcΔT.",
  params="m:Mass:kg:2:0.1:50; c:Specific heat capacity:J/(kg*K):4186:100:5000; dT:Temperature rise:K:30:0:100",
  out="Q:Heat needed:J:m*c*dT; C_cap:Heat capacity of the body:J/K:m*c", plot="dT: Q", eqs="Q = m*c*Delta*T",
  tags="specific heat capacity heat temperature rise water", ask="Q",
  steps="Heat needed is proportional to the mass and to the temperature rise | The constant is the specific heat capacity c | Water's c = 4186 J/(kg K) is unusually large, which is why the sea warms slowly")

X("p11-conduction", 11, P, "Thermal Properties of Matter", "Heat conduction through a wall", "law",
  "Rate of heat flow through a slab.",
  params="k:Thermal conductivity:W/(m*K):0.8:0.02:400; A:Area:m^2:10:0.1:100; dT:Temperature difference:K:20:0:100; L:Thickness:m:0.2:0.01:1",
  out="H:Heat flow rate:W:k*A*dT/L", eqs="H = k*A*dT/L", tags="conduction thermal conductivity heat flow", lab="heat",
  steps="Heat flows from hot to cold at a rate proportional to area and temperature difference | And inversely proportional to thickness | H = kAΔT/L")

X("p11-stefan", 11, P, "Thermal Properties of Matter", "Radiation: Stefan and Wien laws", "law",
  "A hotter body glows brighter and bluer.",
  params="T:Temperature:K:5800:300:30000; A:Surface area:m^2:1:0.01:100; em:Emissivity:-:1:0.01:1",
  out="P:Radiated power:W:em*sigma_SB*A*T**4; lam_max:Peak wavelength:nm:2.898e-3/T*1e9", plot="T: lam_max",
  eqs="P = em*sigma*A*T**4 | lam_max*T = b", tags="stefan boltzmann wien displacement blackbody radiation", lab="blackbody", ask="lam_max,P",
  steps="Stefan's law: power radiated per unit area is σT⁴ times the emissivity | Wien's law: λ_max T = 2.898 × 10⁻³ m K | The Sun (5800 K) peaks near 500 nm")

X("p11-isothermal", 11, P, "Thermodynamics", "Work in an isothermal expansion", "derivation",
  "Area under the P-V curve at constant temperature.",
  params="n:Amount of gas:mol:1:0.1:10; T:Temperature:K:300:100:1000; V1:Initial volume:L:10:1:50; V2:Final volume:L:20:1:100",
  out="W:Work done by the gas:J:n*R_g*T*log(V2/V1); P2:Final pressure:Pa:n*R_g*T/(V2/1000)", plot="V2: W", eqs="W = n*R*T*log(V2/V1)",
  tags="isothermal expansion work thermodynamics", ask="W",
  steps="Work by the gas W = ∫P dV | At constant T, P = nRT/V | ∫ from V1 to V2 of nRT/V dV = nRT ln(V2/V1)")

X("p11-adiabatic", 11, P, "Thermodynamics", "Adiabatic compression", "derivation",
  "No heat in or out: the gas heats up as it is squeezed.",
  params="P1:Initial pressure:kPa:100:10:1000; T1:Initial temperature:K:300:100:1000; ratio:Compression ratio V1/V2:-:8:1:25; gam:Heat capacity ratio:-:1.4:1.1:1.67",
  out="P2:Final pressure:kPa:P1*ratio**gam; T2:Final temperature:K:T1*ratio**(gam - 1)", plot="ratio: T2", eqs="P1*V1**gam = P2*V2**gam | T1*V1**(gam - 1) = T2*V2**(gam - 1)",
  tags="adiabatic process gamma diesel engine compression", ask="T2,P2",
  steps="With no heat exchange, dU = −P dV | For an ideal gas this integrates to PV^γ = constant | Combining with PV = nRT gives TV^(γ−1) = constant")

X("p11-carnot", 11, P, "Thermodynamics", "Carnot engine efficiency", "law",
  "No engine working between two temperatures can beat this.",
  params="Th:Hot reservoir:K:600:300:2000; Tc:Cold reservoir:K:300:100:600; Qh:Heat taken in:J:1000:1:100000",
  out="eta:Efficiency:%:100*(1 - Tc/Th); W:Work done:J:Qh*(1 - Tc/Th); Qc:Heat rejected:J:Qh*Tc/Th", plot="Th: eta",
  eqs="eta = 1 - Tc/Th", tags="carnot heat engine efficiency second law", lab="engine", ask="eta,W",
  steps="For a reversible cycle Qc/Qh = Tc/Th | Efficiency = work/heat in = 1 − Qc/Qh | So η = 1 − Tc/Th")

X("p11-vrms", 11, P, "Kinetic Theory", "RMS speed of gas molecules", "derivation",
  "Molecules move faster in hot, light gases.",
  params="T:Temperature:K:300:50:2000; M:Molar mass:g/mol:28:2:200",
  out="v_rms:RMS speed:m/s:sqrt(3*R_g*T/(M/1000)); v_avg:Mean speed:m/s:sqrt(8*R_g*T/(pi*M/1000)); ke:Mean kinetic energy per molecule:J:1.5*k_B*T",
  plot="T: v_rms", eqs="v_rms = sqrt(3*R*T/M) | KE = 3*k*T/2", tags="kinetic theory rms speed molecules temperature", lab="gas", ask="v_rms",
  steps="Kinetic theory gives P = ⅓ρv²_rms | With PV = nRT and ρ = nM/V: v_rms = √(3RT/M) | Mean kinetic energy per molecule is 3/2 k_B T")

X("p11-ideal-gas", 11, P, "Kinetic Theory", "Ideal gas equation", "law",
  "PV = nRT links pressure, volume and temperature.",
  params="n:Amount of gas:mol:1:0.1:10; T:Temperature:K:300:50:1000; V:Volume:L:24:1:100",
  out="P:Pressure:kPa:n*R_g*T/V; N_mol:Number of molecules:-:n*N_A", plot="V: P", eqs="P*V = n*R*T", scene="gas: P=P, V=V, T=T",
  tags="ideal gas equation pressure volume temperature", lab="gas", ask="P",
  steps="Boyle: P ∝ 1/V at fixed T | Charles: V ∝ T at fixed P | Avogadro: V ∝ n | Together PV = nRT with R = 8.314 J/mol K")

X("p11-shm", 11, P, "Oscillations", "Simple harmonic motion of a spring", "derivation",
  "Displacement, velocity and period of a mass on a spring.",
  params="m:Mass:kg:0.5:0.05:10; k:Spring constant:N/m:20:1:500; A:Amplitude:m:0.1:0.01:0.5",
  out="T:Period:s:2*pi*sqrt(m/k); w:Angular frequency:rad/s:sqrt(k/m); vmax:Maximum speed:m/s:A*sqrt(k/m); amax:Maximum acceleration:m/s^2:A*k/m; E:Total energy:J:k*A**2/2",
  series="x:Displacement:m:A*cos(sqrt(k/m)*t); v:Velocity:m/s:-A*sqrt(k/m)*sin(sqrt(k/m)*t)", plot="t=0..2*T: x, v",
  eqs="T = 2*pi*sqrt(m/k) | x = A*cos(w*t) | a = -w**2*x", scene="spring: amp=A, T=T, m=m",
  tags="simple harmonic motion spring period oscillation", lab="springs", ask="T,vmax",
  steps="Hooke's law gives F = −kx | Newton's law: m d²x/dt² = −kx, so a = −ω²x with ω² = k/m | The solution is x = A cos ωt | One cycle takes T = 2π/ω = 2π√(m/k)")

X("p11-pendulum", 11, P, "Oscillations", "Simple pendulum", "practical",
  "Time period depends on length and g, not on mass.",
  params="L:Length:m:1:0.1:5; g:Acceleration due to gravity:m/s^2:9.8:1.6:25; theta0:Amplitude:deg:5:1:15",
  out="T:Time period:s:2*pi*sqrt(L/g); f:Frequency:Hz:1/(2*pi*sqrt(L/g)); T20:Time for 20 oscillations:s:40*pi*sqrt(L/g)",
  plot="L: T", eqs="T = 2*pi*sqrt(L/g)", scene="pendulum: L=L, amp=theta0, T=T",
  tags="simple pendulum time period length practical", lab="pendulum", ask="T",
  steps="For a small angle θ the restoring force is −mg sin θ ≈ −mgθ | Arc length x = Lθ, so a = −(g/L)x: simple harmonic motion | ω² = g/L, so T = 2π√(L/g) | In the lab, plot T² against L: the slope is 4π²/g")

X("p11-string", 11, P, "Waves", "Vibrating string (sonometer)", "practical",
  "Frequency of a stretched string from tension, length and mass per length.",
  params="Tn:Tension:N:50:1:500; mu:Mass per unit length:g/m:5:0.1:50; L:Vibrating length:m:0.6:0.1:2; nh:Harmonic:-:1:1:6:1",
  out="v:Wave speed:m/s:sqrt(Tn/(mu/1000)); f:Frequency:Hz:nh*sqrt(Tn/(mu/1000))/(2*L); lam:Wavelength:m:2*L/nh",
  plot="L: f", eqs="v = sqrt(Tn/mu) | f = nh*v/(2*L)", tags="sonometer string standing wave frequency tension harmonics", lab="waves", ask="f",
  steps="The wave speed on a string is √(T/μ) | Fixed ends force nodes at both ends: L = n λ/2 | So f = nv/2L")

X("p11-resonance-tube", 11, P, "Waves", "Resonance column: speed of sound", "practical",
  "Two resonance lengths give the speed of sound without the end correction.",
  params="f:Tuning fork frequency:Hz:512:128:1024; l1:First resonance length:cm:16:5:50; l2:Second resonance length:cm:50:15:150",
  out="lam:Wavelength:m:2*(l2 - l1)/100; v:Speed of sound:m/s:2*f*(l2 - l1)/100; e:End correction:cm:(l2 - 3*l1)/2",
  eqs="v = 2*f*(l2 - l1)", tags="resonance column tube speed of sound closed pipe practical", ask="v",
  steps="A closed pipe resonates when l + e = λ/4 and again at 3λ/4 | Subtract: l2 − l1 = λ/2 | So v = fλ = 2f(l2 − l1) | End correction e = (l2 − 3l1)/2")

X("p11-pipes", 11, P, "Waves", "Open and closed organ pipes", "concept",
  "Harmonics in pipes: closed pipes have only odd ones.",
  params="L:Pipe length:m:0.5:0.1:3; v:Speed of sound:m/s:343:300:360; nh:Harmonic number:-:1:1:7:1",
  out="f_open:Open pipe frequency:Hz:nh*v/(2*L); f_closed:Closed pipe frequency:Hz:(2*nh - 1)*v/(4*L)",
  eqs="f_open = nh*v/(2*L) | f_closed = (2*nh - 1)*v/(4*L)", tags="organ pipe open closed harmonics standing waves",
  steps="An open pipe has antinodes at both ends: L = nλ/2 | A closed pipe has a node at the closed end: L = (2n − 1)λ/4 | So a closed pipe gives only odd harmonics", ask="f_open,f_closed")

X("p11-beats", 11, P, "Waves", "Beats", "concept",
  "Two close frequencies make the loudness rise and fall.",
  params="f1:Frequency 1:Hz:256:20:1000; f2:Frequency 2:Hz:260:20:1000",
  out="fb:Beat frequency:Hz:Abs(f1 - f2); Tb:Time between beats:s:1/Abs(f1 - f2)",
  series="y:Combined wave:-:cos(2*pi*f1*t) + cos(2*pi*f2*t)", plot="t=0..2/Abs(f1 - f2): y",
  eqs="fb = Abs(f1 - f2)", tags="beats frequency superposition tuning", lab="interference",
  steps="Add the waves: cos 2πf1t + cos 2πf2t = 2 cos(π(f1 − f2)t) cos(π(f1 + f2)t) | The slow factor is the envelope | Loudness peaks twice per envelope cycle, so the beat frequency is |f1 − f2|", ask="fb")

X("p11-doppler", 11, P, "Waves", "Doppler effect for sound", "law",
  "A horn sounds higher as it approaches and lower as it goes away.",
  params="f:Source frequency:Hz:500:50:5000; vs:Source speed towards the listener:m/s:30:-100:100; vo:Listener speed towards the source:m/s:0:-100:100",
  out="f_heard:Frequency heard:Hz:f*(343 + vo)/(343 - vs)", plot="vs: f_heard", eqs="f_heard = f*(v + vo)/(v - vs)",
  tags="doppler effect sound frequency moving source", lab="doppler", ask="f_heard",
  steps="A moving source squeezes the wavelength in front of it: λ' = (v − vs)/f | A moving listener meets wavefronts faster: relative speed v + vo | f' = (v + vo)/λ' = f(v + vo)/(v − vs)")

X("p11-travelling-wave", 11, P, "Waves", "A travelling wave y = A sin(kx − ωt)", "graph",
  "Amplitude, wavelength and frequency of a progressive wave.",
  params="A:Amplitude:cm:2:0.1:10; lam:Wavelength:m:0.5:0.05:5; f:Frequency:Hz:4:0.1:50",
  out="k:Wave number:rad/m:2*pi/lam; w:Angular frequency:rad/s:2*pi*f; v:Wave speed:m/s:f*lam",
  series="y:Displacement:cm:A*sin(2*pi*x/lam)", plot="x=0..3*lam: y", eqs="y = A*sin(k*x - w*t) | v = w/k",
  scene="wave: lam=lam, f=f", tags="progressive wave equation wave number angular frequency", lab="waves", ask="v",
  steps="A crest at kx − ωt = constant moves with dx/dt = ω/k | k = 2π/λ and ω = 2πf | So v = ω/k = fλ")

# ================================================================ Class 12
X("p12-coulomb", 12, P, "Electric Charges and Fields", "Coulomb's law", "law",
  "Force between two point charges.",
  params="q1:Charge 1:uC:2:-10:10; q2:Charge 2:uC:-3:-10:10; r:Separation:cm:10:1:100",
  out="F:Force (negative means attraction):N:k_e*q1*q2*1e-12/(r/100)**2", plot="r: F", eqs="F = k*q1*q2/r**2",
  scene="field: q=q1, r=r", tags="coulomb law electrostatic force point charges", lab="charges", ask="F",
  steps="The force is proportional to the product of the charges | And inversely proportional to the square of the distance | F = kq1q2/r², k = 1/4πε₀ = 8.99 × 10⁹ N m²/C²")

X("p12-field-point", 12, P, "Electric Charges and Fields", "Field of a point charge", "concept",
  "Electric field strength falls as 1/r².",
  params="q:Charge:nC:5:-50:50; r:Distance:cm:10:1:100",
  out="E:Electric field:N/C:k_e*q*1e-9/(r/100)**2", plot="r: E", eqs="E = k*q/r**2", scene="field: q=q, r=r",
  tags="electric field point charge", lab="charges", ask="E",
  steps="Field is force per unit positive test charge: E = F/q₀ | With Coulomb's law F = kqq₀/r² | So E = kq/r²")

X("p12-dipole", 12, P, "Electric Charges and Fields", "Field of an electric dipole", "derivation",
  "On the axis the field is twice as strong as on the equatorial line.",
  params="q:Charge:nC:10:1:100; a2:Separation 2a:mm:2:0.1:20; r:Distance from centre:cm:10:1:100",
  out="p:Dipole moment:C*m:q*1e-9*a2/1000; E_axial:Axial field:N/C:2*k_e*q*1e-9*a2/1000/(r/100)**3; E_eq:Equatorial field:N/C:k_e*q*1e-9*a2/1000/(r/100)**3",
  plot="r: E_axial, E_eq", eqs="E_axial = 2*k*p/r**3 | E_eq = k*p/r**3", tags="electric dipole axial equatorial field", ask="E_axial",
  steps="On the axis the two fields subtract: kq/(r − a)² − kq/(r + a)² | For r ≫ a this is 4kqa/r³ = 2kp/r³ | On the equatorial line the perpendicular parts cancel, leaving kp/r³")

X("p12-dipole-torque", 12, P, "Electric Charges and Fields", "Dipole in a uniform field", "concept",
  "Torque and potential energy of a dipole.",
  params="p:Dipole moment:C*m:1e-9:1e-12:1e-6; E:Field strength:N/C:1e4:1:1e6; th:Angle to the field:deg:30:0:180",
  out="tau:Torque:N*m:p*E*sin(th*pi/180); U:Potential energy:J:-p*E*cos(th*pi/180)", plot="th: tau, U",
  eqs="tau = p*E*sin(th) | U = -p*E*cos(th)", tags="dipole torque potential energy uniform field", ask="tau",
  steps="The two charges feel equal and opposite forces qE: no net force | They form a couple of arm 2a sin θ | τ = qE × 2a sin θ = pE sin θ | Work to turn it gives U = −pE cos θ")

X("p12-gauss", 12, P, "Electric Charges and Fields", "Gauss's law: line and sheet of charge", "derivation",
  "Fields of an infinite line charge and an infinite plane sheet.",
  params="lam:Line charge density:nC/m:10:0.1:100; sig:Surface charge density:nC/m^2:10:0.1:100; r:Distance from the line:cm:5:0.5:100",
  out="E_line:Field of the line:N/C:lam*1e-9/(2*pi*eps0*r/100); E_sheet:Field of the sheet:N/C:sig*1e-9/(2*eps0)", plot="r: E_line",
  eqs="E_line = lam/(2*pi*eps0*r) | E_sheet = sig/(2*eps0)", tags="gauss law line charge plane sheet flux", ask="E_line,E_sheet",
  steps="Line: take a cylinder of radius r and length l round it | Flux E × 2πrl = charge inside λl / ε₀, so E = λ/2πε₀r | Sheet: a pillbox of area A gives 2EA = σA/ε₀, so E = σ/2ε₀, the same at every distance")

X("p12-potential", 12, P, "Electrostatic Potential and Capacitance", "Potential of a point charge", "concept",
  "Potential falls as 1/r, more slowly than the field.",
  params="q:Charge:nC:5:-50:50; r:Distance:cm:10:1:100",
  out="V:Potential:V:k_e*q*1e-9/(r/100); E:Field:N/C:k_e*q*1e-9/(r/100)**2", plot="r: V", eqs="V = k*q/r",
  tags="electric potential point charge", scene="field: q=q, r=r", ask="V",
  steps="Potential is work per unit charge to bring a test charge from infinity | W = ∫ kq/r² dr from ∞ to r = kq/r | So V = kq/r")

X("p12-capacitor", 12, P, "Electrostatic Potential and Capacitance", "Parallel plate capacitor", "derivation",
  "Capacitance from plate area, gap and dielectric.",
  params="A:Plate area:cm^2:100:1:1000; d:Plate separation:mm:1:0.1:10; K:Dielectric constant:-:1:1:10; V:Voltage:V:12:1:500",
  out="C:Capacitance:pF:K*eps0*(A/1e4)/(d/1000)*1e12; Q:Charge:nC:K*eps0*(A/1e4)/(d/1000)*V*1e9; U:Stored energy:J:K*eps0*(A/1e4)/(d/1000)*V**2/2",
  plot="d: C", eqs="C = K*eps0*A/d | Q = C*V | U = C*V**2/2", tags="capacitor capacitance dielectric energy stored", ask="C,U",
  steps="Field between the plates E = σ/ε₀ = Q/(ε₀A) | Voltage V = Ed = Qd/(ε₀A) | C = Q/V = ε₀A/d; a dielectric multiplies it by K | Energy stored U = ½CV²")

X("p12-cap-combo", 12, P, "Electrostatic Potential and Capacitance", "Capacitors in series and parallel", "concept",
  "The opposite of resistors: parallel capacitances add.",
  params="C1:C1:uF:2:0.1:100; C2:C2:uF:3:0.1:100; C3:C3:uF:6:0.1:100",
  out="Cs:Series combination:uF:1/(1/C1 + 1/C2 + 1/C3); Cp:Parallel combination:uF:C1 + C2 + C3",
  eqs="1/Cs = 1/C1 + 1/C2 + 1/C3 | Cp = C1 + C2 + C3", tags="capacitors series parallel combination", ask="Cs,Cp",
  steps="In series every capacitor carries the same charge and the voltages add: V = Q/C1 + Q/C2 + Q/C3 | In parallel the voltage is the same and the charges add: Q = (C1 + C2 + C3)V")

X("p12-rc", 12, P, "Electrostatic Potential and Capacitance", "Charging a capacitor through a resistor", "concept",
  "The capacitor charges quickly at first, then slowly; the time constant is RC.",
  params="V0:Supply voltage:V:10:1:100; R:Resistance:kohm:10:0.1:1000; C:Capacitance:uF:100:0.1:1000; t:Time:s:1:0:10",
  out="tau:Time constant:s:R*1000*C*1e-6; Vc:Capacitor voltage:V:V0*(1 - exp(-t/(R*1000*C*1e-6))); I:Current:mA:1000*V0/(R*1000)*exp(-t/(R*1000*C*1e-6))",
  series="Vt:Capacitor voltage:V:V0*(1 - exp(-tt/(R*1000*C*1e-6)))", plot="tt=0..5*tau: Vt", eqs="Vc = V0*(1 - exp(-t/(R*C)))",
  tags="rc circuit charging capacitor time constant", lab="rlc", ask="Vc,tau",
  steps="Kirchhoff: V₀ = IR + q/C with I = dq/dt | Solve dq/dt = (CV₀ − q)/RC | q = CV₀(1 − e^(−t/RC)) | After one time constant it reaches 63%")

X("p12-drift", 12, P, "Current Electricity", "Drift velocity of electrons", "derivation",
  "Electrons crawl along a wire even though the current is large.",
  params="I:Current:A:2:0.1:20; dmm:Wire diameter:mm:1:0.2:5; n:Free electron density:1/m^3:8.5e28:1e27:2e29",
  out="vd:Drift velocity:mm/s:1000*I/(n*e_c*pi*(dmm/1000)**2/4)", plot="I: vd", eqs="I = n*e*A*vd",
  tags="drift velocity free electrons current density", ask="vd",
  steps="In time t the electrons move vd t, sweeping a volume A vd t | The charge passing is n e A vd t | Current I = charge/time = neAvd")

X("p12-temp-res", 12, P, "Current Electricity", "Resistance and temperature", "concept",
  "Metals resist more when hot.",
  params="R0:Resistance at 0 °C:ohm:10:1:1000; alpha:Temperature coefficient:1/K:0.0039:0.0001:0.007; Tc:Temperature:degC:100:-50:500",
  out="R:Resistance:ohm:R0*(1 + alpha*Tc)", plot="Tc: R", eqs="R = R0*(1 + alpha*Tc)", tags="temperature coefficient resistance metal thermistor",
  steps="For metals, resistance rises almost linearly with temperature | R = R₀(1 + αΔT) | α for copper is about 0.0039 per kelvin", ask="R")

X("p12-internal", 12, P, "Current Electricity", "EMF and internal resistance", "practical",
  "Terminal voltage drops as more current is drawn.",
  params="Ec:EMF of cell:V:1.5:0.5:24; r:Internal resistance:ohm:0.5:0.01:10; R:External resistance:ohm:5:0.1:100",
  out="I:Current:A:Ec/(R + r); V:Terminal voltage:V:Ec*R/(R + r); P:Power delivered to R:W:Ec**2*R/(R + r)**2", plot="R: V, P",
  eqs="I = Ec/(R + r) | V = Ec - I*r", tags="emf internal resistance terminal voltage cell potentiometer", ask="I,V",
  steps="The cell's own resistance r is in series with the load R | I = E/(R + r) | Terminal voltage V = E − Ir = IR | Power to the load is largest when R = r")

X("p12-metre-bridge", 12, P, "Current Electricity", "Metre bridge: unknown resistance", "practical",
  "Balance point on a one metre wire gives the unknown resistance.",
  params="Rk:Known resistance:ohm:10:1:100; l:Balancing length:cm:40:5:95",
  out="S:Unknown resistance:ohm:Rk*(100 - l)/l", plot="l: S", eqs="S = Rk*(100 - l)/l", tags="metre bridge wheatstone bridge unknown resistance practical",
  steps="At balance the galvanometer shows no current: a Wheatstone bridge | R/S = (resistance of l cm)/(resistance of 100 − l cm) | For a uniform wire this is l/(100 − l) | So S = R(100 − l)/l", ask="S")

X("p12-potentiometer", 12, P, "Current Electricity", "Potentiometer: comparing two cells", "practical",
  "Balancing lengths are proportional to EMF.",
  params="E1:EMF of cell 1:V:1.5:0.5:3; l1:Balancing length for cell 1:cm:300:50:1000; l2:Balancing length for cell 2:cm:220:50:1000",
  out="E2:EMF of cell 2:V:E1*l2/l1; ratio:E1/E2:-:l1/l2", eqs="E1/E2 = l1/l2", tags="potentiometer emf comparison practical", ask="E2",
  steps="With a steady current, potential drop along the wire is proportional to length | At balance no current flows through the cell, so its full EMF is measured | E1/E2 = l1/l2")

X("p12-kirchhoff", 12, P, "Current Electricity", "Kirchhoff's laws: two cells in parallel", "derivation",
  "Loop and junction rules solve a two-loop circuit.",
  params="E1:EMF 1:V:12:0:24; r1:Resistance in branch 1:ohm:2:0.1:20; E2:EMF 2:V:6:0:24; r2:Resistance in branch 2:ohm:4:0.1:20; R:Load:ohm:10:0.1:100",
  out="V:Voltage across load:V:(E1/r1 + E2/r2)/(1/r1 + 1/r2 + 1/R); I:Load current:A:(E1/r1 + E2/r2)/(1/r1 + 1/r2 + 1/R)/R; I1:Current from cell 1:A:(E1 - (E1/r1 + E2/r2)/(1/r1 + 1/r2 + 1/R))/r1; I2:Current from cell 2:A:(E2 - (E1/r1 + E2/r2)/(1/r1 + 1/r2 + 1/R))/r2",
  eqs="I1 + I2 = I | E1 - I1*r1 = I*R | E2 - I2*r2 = I*R", tags="kirchhoff junction loop rule circuit", ask="I",
  steps="Junction rule: current in = current out, I1 + I2 = I | Loop rule for each cell's loop: E − I r = V across the load | Write each current in terms of V and add them: (E1 − V)/r1 + (E2 − V)/r2 = V/R | Solve for V")

X("p12-cyclotron", 12, P, "Moving Charges and Magnetism", "Charged particle in a magnetic field", "derivation",
  "Circular path, radius and cyclotron frequency.",
  params="v:Speed:m/s:1e6:1e4:1e7; B:Magnetic field:T:0.5:0.01:3; mass_u:Mass (in u):-:1:0.00054858:4; qe:Charge (in e):-:1:1:2:1",
  out="r:Radius of path:mm:1000*mass_u*1.66054e-27*v/(qe*e_c*B); f:Cyclotron frequency:MHz:qe*e_c*B/(2*pi*mass_u*1.66054e-27)/1e6",
  plot="B: r", eqs="r = m*v/(q*B) | f = q*B/(2*pi*m)", tags="cyclotron circular motion magnetic field lorentz force radius", lab="lorentz", ask="r",
  steps="The magnetic force qvB is always perpendicular to v, so it is a centripetal force | qvB = mv²/r gives r = mv/qB | Period T = 2πr/v = 2πm/qB does not depend on speed, which is why a cyclotron works")

X("p12-loop", 12, P, "Moving Charges and Magnetism", "Field on the axis of a circular loop", "derivation",
  "Biot-Savart law for a current loop.",
  params="I:Current:A:5:0.1:50; R:Loop radius:cm:10:1:50; N_t:Turns:-:1:1:500:1; x:Distance along the axis:cm:0:0:100",
  out="B:Field on the axis:T:mu0*N_t*I*(R/100)**2/(2*((R/100)**2 + (x/100)**2)**1.5); B0:Field at the centre:T:mu0*N_t*I/(2*R/100)",
  plot="x: B", eqs="B = mu0*N_t*I*R**2/(2*(R**2 + x**2)**(3/2)) | B0 = mu0*N_t*I/(2*R)", tags="biot savart circular loop coil field axis", ask="B0,B",
  steps="Each element dl gives dB = μ₀I dl/(4π(R² + x²)), perpendicular to the line joining it | Components across the axis cancel round the loop | Along the axis dB cos α adds up with cos α = R/√(R² + x²) | B = μ₀IR²/2(R² + x²)^(3/2); at the centre B = μ₀I/2R")

X("p12-parallel-wires", 12, P, "Moving Charges and Magnetism", "Force between parallel currents", "law",
  "Currents in the same direction attract.",
  params="I1:Current 1:A:10:0.1:100; I2:Current 2:A:10:0.1:100; d:Separation:cm:5:0.5:100",
  out="F_L:Force per metre:N/m:mu0*I1*I2/(2*pi*d/100)", plot="d: F_L", eqs="F_L = mu0*I1*I2/(2*pi*d)",
  tags="parallel conductors force ampere definition", ask="F_L",
  steps="Wire 1 makes a field B = μ₀I1/2πd at wire 2 | Force per length on wire 2 is I2B | F/L = μ₀I1I2/2πd")

X("p12-ammeter", 12, P, "Moving Charges and Magnetism", "Galvanometer to ammeter and voltmeter", "practical",
  "The shunt or series resistance needed to convert a galvanometer.",
  params="G:Galvanometer resistance:ohm:50:1:500; Ig:Full-scale current:mA:5:0.1:50; I:Ammeter range:A:5:0.1:20; Vr:Voltmeter range:V:10:1:300",
  out="S:Shunt for the ammeter:ohm:(Ig/1000)*G/(I - Ig/1000); Rs:Series resistance for the voltmeter:ohm:Vr/(Ig/1000) - G",
  eqs="S = Ig*G/(I - Ig) | Rs = V/Ig - G", tags="galvanometer ammeter voltmeter shunt conversion practical", ask="S,Rs",
  steps="Ammeter: a small shunt S in parallel carries I − Ig while Ig flows through G | Same voltage: IgG = (I − Ig)S | Voltmeter: a large Rs in series so that Ig(G + Rs) = V")

X("p12-coil-torque", 12, P, "Moving Charges and Magnetism", "Torque on a current loop", "concept",
  "The principle of the electric motor and the moving coil galvanometer.",
  params="N_t:Turns:-:100:1:1000:1; I:Current:A:0.5:0:10; A:Coil area:cm^2:20:1:200; B:Field:T:0.2:0.01:2; th:Angle between normal and field:deg:90:0:180",
  out="tau:Torque:N*m:N_t*I*(A/1e4)*B*sin(th*pi/180); m:Magnetic moment:A*m^2:N_t*I*A/1e4", plot="th: tau",
  eqs="tau = N_t*I*A*B*sin(th)", tags="torque coil motor galvanometer magnetic moment", ask="tau",
  steps="Forces on the two long sides are equal and opposite, forming a couple | Each is NIbB and their arm is a sin θ | τ = NIabB sin θ = NIAB sin θ")

X("p12-generator", 12, P, "Electromagnetic Induction", "AC generator", "derivation",
  "A coil turning in a field makes a sinusoidal EMF.",
  params="N_t:Turns:-:100:1:1000:1; B:Field:T:0.1:0.01:2; A:Coil area:cm^2:100:1:1000; f:Rotation frequency:Hz:50:1:100",
  out="E0:Peak EMF:V:N_t*B*(A/1e4)*2*pi*f; Erms:RMS EMF:V:N_t*B*(A/1e4)*2*pi*f/sqrt(2)",
  series="emf:EMF:V:N_t*B*(A/1e4)*2*pi*f*sin(2*pi*f*t)", plot="t=0..2/f: emf", eqs="emf = N_t*B*A*w*sin(w*t) | E0 = N_t*B*A*w",
  tags="ac generator faraday law induced emf rotating coil", lab="faraday", ask="E0",
  steps="Flux through the coil Φ = NBA cos ωt | Faraday: e = −dΦ/dt = NBAω sin ωt | The peak EMF is NBAω")

X("p12-motional", 12, P, "Electromagnetic Induction", "Motional EMF", "derivation",
  "A rod sliding on rails in a magnetic field.",
  params="B:Field:T:0.5:0.01:2; l:Rod length:m:0.5:0.05:2; v:Speed:m/s:4:0:20; R:Circuit resistance:ohm:2:0.1:50",
  out="emf:Induced EMF:V:B*l*v; I:Current:A:B*l*v/R; F:Force needed to keep it moving:N:B**2*l**2*v/R", plot="v: emf",
  eqs="emf = B*l*v", tags="motional emf rod rails induction lenz", ask="emf",
  steps="The rod sweeps area lv each second | The flux changes at Blv per second | Faraday: e = Blv | The induced current feels a force opposing the motion (Lenz's law)")

X("p12-inductance", 12, P, "Electromagnetic Induction", "Self-inductance of a solenoid", "derivation",
  "L = μ₀n²Al and the energy stored in the field.",
  params="N_t:Turns:-:1000:10:5000:10; A:Cross-section:cm^2:5:0.5:50; l:Length:cm:20:2:100; I:Current:A:2:0:20",
  out="L:Inductance:mH:1000*mu0*N_t**2*(A/1e4)/(l/100); U:Stored energy:J:mu0*N_t**2*(A/1e4)/(l/100)*I**2/2",
  eqs="L = mu0*n**2*A*l | U = L*I**2/2", tags="self inductance solenoid energy magnetic field", ask="L",
  steps="Field inside B = μ₀nI with n = N/l | Total flux linkage NΦ = N × μ₀nI × A | L = NΦ/I = μ₀n²Al | Energy stored U = ½LI²")

X("p12-lr", 12, P, "Electromagnetic Induction", "Growth of current in an LR circuit", "concept",
  "An inductor slows down the rise of current.",
  params="Ec:Supply EMF:V:12:1:100; R:Resistance:ohm:10:0.1:100; L:Inductance:H:0.5:0.01:10; t:Time:s:0.05:0:2",
  out="tau:Time constant:s:L/R; I:Current:A:Ec/R*(1 - exp(-R*t/L))", series="It:Current:A:Ec/R*(1 - exp(-R*tt/L))",
  plot="tt=0..5*L/R: It", eqs="I = Ec/R*(1 - exp(-R*t/L))", tags="lr circuit inductor time constant growth", lab="rlc", ask="I,tau",
  steps="Loop: E = IR + L dI/dt | Separate and integrate | I = (E/R)(1 − e^(−Rt/L)) | The time constant is L/R")

X("p12-ac-rms", 12, P, "Alternating Current", "Peak and RMS values", "derivation",
  "Why a 230 V supply peaks at about 325 V.",
  params="V0:Peak voltage:V:325:1:1000; R:Resistance:ohm:100:1:1000",
  out="Vrms:RMS voltage:V:V0/sqrt(2); Irms:RMS current:A:V0/(sqrt(2)*R); P:Average power:W:V0**2/(2*R)",
  series="v:Voltage:V:V0*sin(2*pi*50*t)", plot="t=0..0.04: v", eqs="Vrms = V0/sqrt(2) | P = Vrms**2/R",
  tags="ac rms peak value average power alternating", ask="Vrms,P",
  steps="The heating effect depends on the mean of V² | The mean of sin² over a cycle is ½ | So V_rms = √(mean V²) = V₀/√2")

X("p12-lcr", 12, P, "Alternating Current", "Series LCR circuit and resonance", "derivation",
  "Impedance, current and the sharp peak at resonance.",
  params="Vrms:Supply RMS voltage:V:220:1:500; R:Resistance:ohm:20:1:500; L:Inductance:H:0.2:0.001:2; C:Capacitance:uF:50:0.1:500; f:Frequency:Hz:50:1:500",
  out="XL:Inductive reactance:ohm:2*pi*f*L; XC:Capacitive reactance:ohm:1/(2*pi*f*C*1e-6); Z:Impedance:ohm:sqrt(R**2 + (2*pi*f*L - 1/(2*pi*f*C*1e-6))**2); I:RMS current:A:Vrms/sqrt(R**2 + (2*pi*f*L - 1/(2*pi*f*C*1e-6))**2); f0:Resonant frequency:Hz:1/(2*pi*sqrt(L*C*1e-6)); phi:Phase angle:deg:atan((2*pi*f*L - 1/(2*pi*f*C*1e-6))/R)*180/pi; Qf:Quality factor:-:sqrt(L/(C*1e-6))/R",
  plot="f: I", eqs="Z = sqrt(R**2 + (XL - XC)**2) | f0 = 1/(2*pi*sqrt(L*C))", tags="lcr circuit resonance impedance reactance quality factor",
  lab="resonance", ask="Z,f0",
  steps="Voltages across L and C are 180° apart, so they subtract: V² = V_R² + (V_L − V_C)² | Divide by I²: Z² = R² + (X_L − X_C)² | Current is largest when X_L = X_C, i.e. ω²LC = 1 | So f₀ = 1/2π√(LC)")

X("p12-transformer", 12, P, "Alternating Current", "Transformer", "law",
  "Stepping voltage up or down with a turns ratio.",
  params="Vp:Primary voltage:V:230:1:11000; Np:Primary turns:-:1000:10:10000:10; Ns:Secondary turns:-:50:10:10000:10; Ip:Primary current:A:1:0.01:100; eta:Efficiency:%:100:50:100",
  out="Vs:Secondary voltage:V:Vp*Ns/Np; Is:Secondary current:A:eta/100*Vp*Ip/(Vp*Ns/Np)", eqs="Vs/Vp = Ns/Np | Vp*Ip = Vs*Is",
  tags="transformer step up step down turns ratio", ask="Vs,Is",
  steps="The same changing flux links both coils, so EMF per turn is equal: Vs/Ns = Vp/Np | For an ideal transformer power in = power out: VpIp = VsIs")

X("p12-em-waves", 12, P, "Electromagnetic Waves", "The electromagnetic spectrum", "concept",
  "Wavelength, frequency and photon energy across the spectrum.",
  params="lognu:Frequency (log10 of Hz):-:14.7:4:20",
  out="f:Frequency:Hz:10**lognu; lam:Wavelength:m:c0/10**lognu; E:Photon energy:eV:h_P*10**lognu/eV", plot="lognu: E",
  eqs="c = f*lam | E = h*f", tags="electromagnetic spectrum radio microwave infrared visible ultraviolet x ray gamma",
  steps="All electromagnetic waves travel at c in vacuum | c = fλ | Each photon carries E = hf; visible light is about 1.7 to 3.1 eV", ask="lam")

X("p12-lensmaker", 12, P, "Ray Optics and Optical Instruments", "Lens maker's formula", "derivation",
  "Focal length from the glass and the curvature of the faces.",
  params="n:Refractive index:-:1.5:1.3:2; R1:Radius of first surface:cm:20:-100:100; R2:Radius of second surface:cm:-20:-100:100",
  out="f:Focal length:cm:1/((n - 1)*(1/R1 - 1/R2)); P:Power:D:100*(n - 1)*(1/R1 - 1/R2)", eqs="1/f = (n - 1)*(1/R1 - 1/R2)",
  tags="lens maker formula curvature focal length", ask="f",
  steps="Apply refraction at a spherical surface to each face in turn | The image from the first face is the object for the second | Adding the two equations for a thin lens gives 1/f = (n − 1)(1/R1 − 1/R2)")

X("p12-tir", 12, P, "Ray Optics and Optical Instruments", "Total internal reflection", "concept",
  "Critical angle, optical fibres and why diamonds sparkle.",
  params="n1:Denser medium index:-:1.5:1.1:2.42; n2:Rarer medium index:-:1:1:1.4",
  out="C:Critical angle:deg:asin(n2/n1)*180/pi", eqs="sin(C) = n2/n1", tags="total internal reflection critical angle optical fibre",
  steps="At the critical angle the refracted ray grazes the surface: r = 90° | Snell: n1 sin C = n2 sin 90° | So sin C = n2/n1; beyond C all light is reflected", ask="C")

X("p12-min-dev", 12, P, "Ray Optics and Optical Instruments", "Prism: minimum deviation", "practical",
  "Refractive index from the angle of minimum deviation.",
  params="A:Angle of prism:deg:60:30:75; dm:Angle of minimum deviation:deg:38:10:70",
  out="n:Refractive index:-:sin((A + dm)*pi/360)/sin(A*pi/360); i:Angle of incidence at minimum deviation:deg:(A + dm)/2",
  plot="dm: n", eqs="n = sin((A + dm)/2)/sin(A/2)", tags="prism minimum deviation refractive index practical spectrometer", ask="n",
  steps="At minimum deviation the ray passes symmetrically: r1 = r2 = A/2 and i = e | δm = 2i − A, so i = (A + δm)/2 | n = sin i / sin r = sin((A + δm)/2)/sin(A/2)")

X("p12-telescope", 12, P, "Ray Optics and Optical Instruments", "Astronomical telescope and microscope", "concept",
  "Magnifying power of optical instruments.",
  params="fo:Objective focal length:cm:100:1:500; fe:Eyepiece focal length:cm:5:0.5:20; Lm:Microscope tube length:cm:16:5:30; fo_m:Microscope objective focal length:cm:0.5:0.1:3",
  out="M_tel:Telescope magnification (normal adjustment):-:fo/fe; L_tel:Telescope length:cm:fo + fe; M_mic:Microscope magnification (image at 25 cm):-:(Lm/fo_m)*(1 + 25/fe)",
  eqs="M_tel = fo/fe | M_mic = (Lm/fo_m)*(1 + D/fe)", tags="telescope microscope magnifying power optical instruments", ask="M_tel",
  steps="Telescope: the objective forms an image at its focus; the eyepiece views it from its own focus | Angular magnification = fo/fe | Microscope: the objective magnifies by about L/fo and the eyepiece by 1 + D/fe")

X("p12-ydse", 12, P, "Wave Optics", "Young's double slit experiment", "derivation",
  "Fringe width and the intensity pattern on the screen.",
  params="lam:Wavelength:nm:600:380:750; d:Slit separation:mm:0.5:0.05:2; D:Screen distance:m:1:0.2:3; y:Position on screen:mm:0:-5:5",
  out="beta:Fringe width:mm:1000*lam*1e-9*D/(d/1000); I_rel:Relative intensity at y:-:cos(pi*(d/1000)*(y/1000)/(lam*1e-9*D))**2",
  series="Iy:Relative intensity:-:cos(pi*(d/1000)*(yy/1000)/(lam*1e-9*D))**2", plot="yy=-5..5: Iy",
  eqs="beta = lam*D/d | I = 4*I0*cos(pi*d*y/(lam*D))**2", tags="young double slit interference fringe width", lab="interference", ask="beta",
  steps="Path difference at a point y on the screen is Δ = yd/D | Bright fringes where Δ = nλ: y = nλD/d | The spacing between them is β = λD/d | Adding the two waves gives I = 4I₀cos²(πΔ/λ)")

X("p12-single-slit", 12, P, "Wave Optics", "Diffraction at a single slit", "derivation",
  "The central bright band is twice as wide as the others.",
  params="lam:Wavelength:nm:600:380:750; a:Slit width:mm:0.1:0.01:1; D:Screen distance:m:1:0.2:3",
  out="w:Width of central maximum:mm:2000*lam*1e-9*D/(a/1000); th1:Angle of first minimum:deg:asin(lam*1e-9/(a/1000))*180/pi",
  series="Iy:Relative intensity:-:(sin(pi*(a/1000)*(yy/1000)/(lam*1e-9*D))/(pi*(a/1000)*(yy/1000)/(lam*1e-9*D) + 1e-12))**2", plot="yy=-15..15: Iy",
  eqs="a*sin(th1) = lam | w = 2*lam*D/a", tags="single slit diffraction central maximum", ask="w",
  steps="Split the slit into two halves | At a sin θ = λ each point in one half cancels a point in the other | So the first minima are at sin θ = ±λ/a | Central maximum width on the screen is 2λD/a")

X("p12-malus", 12, P, "Wave Optics", "Malus's law", "law",
  "Light through two polaroids.",
  params="I0:Intensity after first polaroid:W/m^2:100:1:1000; th:Angle between polaroids:deg:30:0:180",
  out="I:Transmitted intensity:W/m^2:I0*cos(th*pi/180)**2", plot="th: I", eqs="I = I0*cos(th)**2",
  tags="malus law polarisation polaroid", ask="I",
  steps="The second polaroid passes only the component E cos θ | Intensity goes as the square of the amplitude | I = I₀ cos² θ")

X("p12-brewster", 12, P, "Wave Optics", "Brewster's angle", "law",
  "Reflected light is fully polarised at this angle.",
  params="n:Refractive index:-:1.5:1.1:2.5",
  out="thB:Brewster angle:deg:atan(n)*180/pi; r:Refraction angle:deg:90 - atan(n)*180/pi", eqs="tan(thB) = n",
  tags="brewster angle polarisation reflection", ask="thB",
  steps="At Brewster's angle the reflected and refracted rays are at 90° | So r = 90° − i | Snell: sin i = n sin(90° − i) = n cos i | tan i = n")

X("p12-photoelectric", 12, P, "Dual Nature of Radiation and Matter", "Photoelectric effect", "law",
  "Einstein's equation: maximum kinetic energy and stopping potential.",
  params="lam:Wavelength of light:nm:300:100:800; phi:Work function:eV:2.3:1:6",
  out="E:Photon energy:eV:1239.84/lam; Kmax:Maximum kinetic energy:eV:Max(0, 1239.84/lam - phi); V0:Stopping potential:V:Max(0, 1239.84/lam - phi); lam0:Threshold wavelength:nm:1239.84/phi",
  plot="lam: Kmax", eqs="Kmax = h*f - phi | e*V0 = Kmax", tags="photoelectric effect einstein work function stopping potential threshold",
  lab="photoelectric", ask="Kmax,lam0",
  steps="Light comes in photons of energy hf = hc/λ | An electron absorbs one photon and must spend φ to escape | K_max = hf − φ | No emission below the threshold frequency f₀ = φ/h, however bright the light")

X("p12-de-broglie", 12, P, "Dual Nature of Radiation and Matter", "De Broglie wavelength of an electron", "derivation",
  "Electrons accelerated through a voltage behave like waves.",
  params="V:Accelerating voltage:V:100:1:50000",
  out="lam:Wavelength:nm:h_P/sqrt(2*m_e*e_c*V)*1e9; p:Momentum:kg*m/s:sqrt(2*m_e*e_c*V)", plot="V: lam",
  eqs="lam = h/p | lam = h/sqrt(2*m*e*V)", tags="de broglie wavelength electron matter wave", ask="lam",
  steps="Kinetic energy gained eV = p²/2m | So p = √(2meV) | De Broglie: λ = h/p = h/√(2meV) ≈ 1.227/√V nm")

X("p12-bohr", 12, P, "Atoms", "Bohr model of hydrogen", "derivation",
  "Radius and energy of the allowed orbits.",
  params="n:Orbit number:-:2:1:7:1; Z:Atomic number:-:1:1:3:1",
  out="r:Orbit radius:nm:0.0529177*n**2/Z; E:Energy:eV:-13.6057*Z**2/n**2; v:Electron speed:m/s:2.18769e6*Z/n", plot="n: E",
  eqs="r = a0*n**2/Z | E = -13.6*Z**2/n**2", scene="atom: n=n, Z=Z, r=r", tags="bohr model hydrogen energy levels orbit radius",
  lab="hydrogen", ask="E,r",
  steps="Angular momentum is quantised: mvr = nh/2π | Coulomb force gives the centripetal force: kZe²/r² = mv²/r | Solve: r = n²a₀/Z | Total energy E = −kZe²/2r = −13.6 Z²/n² eV")

X("p12-spectrum", 12, P, "Atoms", "Spectral lines of hydrogen", "law",
  "Rydberg formula for the Lyman, Balmer and Paschen series.",
  params="n1:Lower level:-:2:1:4:1; n2:Upper level:-:3:2:8:1",
  out="lam:Wavelength:nm:1e9/(R_H*(1/n1**2 - 1/n2**2)); E:Photon energy:eV:13.6057*(1/n1**2 - 1/n2**2)",
  eqs="1/lam = R*(1/n1**2 - 1/n2**2)", tags="hydrogen spectrum rydberg lyman balmer paschen", lab="hydrogen", ask="lam",
  steps="A jump from n2 to n1 releases the energy difference 13.6(1/n1² − 1/n2²) eV | E = hc/λ | So 1/λ = R(1/n1² − 1/n2²) with R = 1.097 × 10⁷ m⁻¹ | n1 = 2 gives the visible Balmer series")

X("p12-binding", 12, P, "Nuclei", "Mass defect and binding energy", "concept",
  "Energy that holds a nucleus together.",
  params="Z:Protons:-:2:1:92:1; A:Mass number:-:4:1:238:1; M:Atomic mass:u:4.002602:1:240",
  out="dm:Mass defect:u:Z*1.007825 + (A - Z)*1.008665 - M; BE:Binding energy:MeV:931.494*(Z*1.007825 + (A - Z)*1.008665 - M); BEA:Binding energy per nucleon:MeV:931.494*(Z*1.007825 + (A - Z)*1.008665 - M)/A",
  eqs="dm = Z*mH + (A - Z)*mn - M | BE = dm*c**2 | E = m*c**2", tags="mass defect binding energy nucleus einstein", ask="BE,BEA",
  steps="Add the masses of the separate hydrogen atoms and neutrons | Subtract the measured atomic mass: that is the mass defect | E = Δmc² with 1 u = 931.5 MeV")

X("p12-decay", 12, P, "Nuclei", "Radioactive decay law", "derivation",
  "Exponential decay, half-life and activity.",
  params="N0:Initial nuclei:-:1e6:1000:1e12; T_half:Half-life:s:10:0.1:1000; t:Time:s:20:0:5000",
  out="lam:Decay constant:1/s:log(2)/T_half; N:Nuclei left:-:N0*exp(-log(2)*t/T_half); A:Activity:Bq:log(2)/T_half*N0*exp(-log(2)*t/T_half); tau:Mean life:s:T_half/log(2)",
  series="Nt:Nuclei left:-:N0*exp(-log(2)*tt/T_half)", plot="tt=0..6*T_half: Nt", eqs="N = N0*exp(-lam*t) | T_half = log(2)/lam",
  scene="decay: N0=N0, N=N, half=T_half", tags="radioactive decay constant half life activity mean life", lab="decay", ask="N,A",
  steps="Each nucleus has the same chance of decaying per second: dN/dt = −λN | Integrate: N = N₀e^(−λt) | Half-life: ½ = e^(−λT½), so T½ = ln 2/λ | Activity A = λN")

X("p12-diode", 12, P, "Semiconductor Electronics", "p-n junction diode characteristic", "practical",
  "Current through a diode grows exponentially in forward bias.",
  params="Is:Saturation current:nA:1:0.001:100; eta:Ideality factor:-:1.5:1:2; V:Applied voltage:V:0.6:-1:0.8; Tk:Temperature:K:300:250:400",
  out="VT:Thermal voltage:mV:1000*k_B*Tk/e_c; I:Current:mA:1e-6*Is*(exp(V/(eta*k_B*Tk/e_c)) - 1)", plot="V: I",
  eqs="I = Is*(exp(V/(eta*VT)) - 1)", tags="diode characteristic forward reverse bias semiconductor practical", ask="I",
  steps="In forward bias the barrier is lowered and carriers diffuse across | The current rises as e^(V/ηV_T) | In reverse bias only the tiny saturation current flows")

X("p12-rectifier", 12, P, "Semiconductor Electronics", "Half and full wave rectifier", "concept",
  "Average DC output from an AC input.",
  params="Vm:Peak input:V:12:1:50; Vd:Diode drop:V:0.7:0:1",
  out="Vdc_half:Half-wave average:V:(Vm - Vd)/pi; Vdc_full:Full-wave average:V:2*(Vm - Vd)/pi",
  series="vout:Full-wave output:V:Max(0, Abs(Vm*sin(2*pi*50*t)) - Vd)", plot="t=0..0.04: vout",
  eqs="Vdc_full = 2*Vm/pi | Vdc_half = Vm/pi", tags="rectifier half wave full wave diode dc", ask="Vdc_full",
  steps="A half-wave rectifier passes only the positive half cycles; the average of a half sine over a full cycle is Vm/π | A full-wave rectifier flips the negative halves, doubling the average to 2Vm/π")
