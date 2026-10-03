"""ASM Teach mathematics: Class 9 to 12. Chapters follow the NCERT textbooks; ICSE-only topics are tagged with their boards."""
from app.modules.teach.core import X

M = "mathematics"
ICSE = ("ICSE", "State")

# ================================================================ Class 9
X("m9-polynomial", 9, M, "Polynomials", "Value and zeros of a quadratic polynomial", "graph",
  "p(x) = ax² + bx + c: evaluate it and see where it crosses the x-axis.",
  params="a:a:-:1:-5:5; b:b:-:-3:-10:10; c:c:-:2:-10:10; x0:Evaluate at x:-:1:-10:10",
  out="p0:p(x0):-:a*x0**2 + b*x0 + c", series="y:p(x):-:a*x**2 + b*x + c", plot="x=-6..6: y",
  eqs="p = a*x**2 + b*x + c", scene="graph", tags="polynomial value zero remainder theorem quadratic",
  steps="Substitute x₀ for x and simplify | By the remainder theorem p(x₀) is the remainder when p(x) is divided by x − x₀ | If p(x₀) = 0, then x − x₀ is a factor", ask="p0")

X("m9-cubic", 9, M, "Polynomials", "Factor theorem for a cubic", "graph",
  "x³ + bx² + cx + d: test whether x − k is a factor.",
  params="b:b:-:-6:-10:10; c:c:-:11:-20:20; d:d:-:-6:-20:20; k:k:-:1:-5:5",
  out="pk:p(k):-:k**3 + b*k**2 + c*k + d", series="y:p(x):-:x**3 + b*x**2 + c*x + d", plot="x=-2..5: y",
  eqs="p = x**3 + b*x**2 + c*x + d", scene="graph", tags="factor theorem cubic polynomial remainder",
  steps="Compute p(k) | If p(k) = 0, x − k is a factor | Here x³ − 6x² + 11x − 6 = (x − 1)(x − 2)(x − 3)", ask="pk")

X("m9-linear-eq", 9, M, "Linear Equations in Two Variables", "Graph of a linear equation", "graph",
  "ax + by = c is a straight line; every point on it is a solution.",
  params="a:a:-:2:-10:10; b:b:-:3:0.5:10; c:c:-:12:-20:20",
  out="yint:y-intercept:-:c/b; xint:x-intercept:-:c/a; slope:Slope:-:-a/b", series="y:y:-:(c - a*x)/b", plot="x=-10..10: y",
  eqs="a*x + b*y = c", scene="graph", tags="linear equation two variables graph straight line solution",
  steps="Rearrange for y: y = (c − ax)/b | Put x = 0 for the y-intercept c/b and y = 0 for the x-intercept c/a | Join them for the line", ask="yint")

X("m9-heron", 9, M, "Heron's Formula", "Heron's formula", "derivation",
  "Area of a triangle from its three sides.",
  params="a:Side a:cm:5:1:30; b:Side b:cm:6:1:30; c:Side c:cm:7:1:30",
  out="s:Semi-perimeter:cm:(a + b + c)/2; A:Area:cm^2:sqrt((a + b + c)/2*((a + b + c)/2 - a)*((a + b + c)/2 - b)*((a + b + c)/2 - c))",
  eqs="A = sqrt(s*(s - a)*(s - b)*(s - c))", scene="shape: kind=triangle, a=a, b=b, c=c", tags="heron formula area triangle sides semi perimeter",
  steps="Find the semi-perimeter s = (a + b + c)/2 | Area = √(s(s − a)(s − b)(s − c)) | The three sides must satisfy the triangle inequality or the area is not real", ask="A")

X("m9-cuboid", 9, M, "Surface Areas and Volumes", "Cuboid and cube", "concept",
  "Surface area and volume of a box.",
  params="l:Length:cm:10:1:100; b:Breadth:cm:6:1:100; h:Height:cm:4:1:100",
  out="TSA:Total surface area:cm^2:2*(l*b + b*h + h*l); LSA:Lateral surface area:cm^2:2*h*(l + b); V:Volume:cm^3:l*b*h; d:Diagonal:cm:sqrt(l**2 + b**2 + h**2)",
  eqs="TSA = 2*(l*b + b*h + h*l) | V = l*b*h", scene="shape: kind=cuboid, a=l, b=b, c=h", tags="cuboid cube surface area volume diagonal",
  steps="A cuboid has three pairs of equal rectangular faces: lb, bh, hl | Total surface area is twice their sum | Volume = l × b × h", ask="TSA,V")

X("m9-cylinder", 9, M, "Surface Areas and Volumes", "Right circular cylinder", "concept",
  "Curved surface, total surface and volume.",
  params="r:Radius:cm:7:0.5:50; h:Height:cm:10:0.5:100",
  out="CSA:Curved surface area:cm^2:2*pi*r*h; TSA:Total surface area:cm^2:2*pi*r*(r + h); V:Volume:cm^3:pi*r**2*h",
  plot="r: V", eqs="CSA = 2*pi*r*h | V = pi*r**2*h", scene="shape: kind=cylinder, a=r, b=h", tags="cylinder curved surface area volume",
  steps="Unroll the curved surface into a rectangle of sides 2πr and h | Add two circular ends for the total surface | Volume = base area × height = πr²h", ask="CSA,V")

X("m9-cone", 9, M, "Surface Areas and Volumes", "Right circular cone", "concept",
  "Slant height, surface area and volume.",
  params="r:Radius:cm:7:0.5:50; h:Height:cm:24:0.5:100",
  out="l:Slant height:cm:sqrt(r**2 + h**2); CSA:Curved surface area:cm^2:pi*r*sqrt(r**2 + h**2); TSA:Total surface area:cm^2:pi*r*(sqrt(r**2 + h**2) + r); V:Volume:cm^3:pi*r**2*h/3",
  eqs="l = sqrt(r**2 + h**2) | CSA = pi*r*l | V = pi*r**2*h/3", scene="shape: kind=cone, a=r, b=h", tags="cone slant height surface area volume",
  steps="The slant height is the hypotenuse: l = √(r² + h²) | Opened out, the curved surface is a sector of area πrl | A cone holds one third of the cylinder with the same base and height", ask="l,V")

X("m9-sphere", 9, M, "Surface Areas and Volumes", "Sphere and hemisphere", "concept",
  "Surface area 4πr² and volume 4/3 πr³.",
  params="r:Radius:cm:7:0.5:50",
  out="SA:Surface area of sphere:cm^2:4*pi*r**2; V:Volume of sphere:cm^3:4*pi*r**3/3; TSA_h:Total surface of hemisphere:cm^2:3*pi*r**2; V_h:Volume of hemisphere:cm^3:2*pi*r**3/3",
  plot="r: SA, V", eqs="SA = 4*pi*r**2 | V = 4*pi*r**3/3", scene="shape: kind=sphere, a=r", tags="sphere hemisphere surface area volume",
  steps="The surface area of a sphere is four times the area of its great circle: 4πr² | Its volume is 4/3 πr³ | A hemisphere has half the curved surface plus a flat circle: 3πr²", ask="SA,V")

X("m9-angle-sum", 9, M, "Lines and Angles", "Angle sum of a triangle", "concept",
  "The three angles always add up to 180°; the exterior angle equals the two opposite interior angles.",
  params="A:Angle A:deg:50:1:178; B:Angle B:deg:60:1:178",
  out="C:Angle C:deg:180 - A - B; ext:Exterior angle at C:deg:A + B", eqs="A + B + C = 180 | ext = A + B",
  scene="shape: kind=triangle_angles, a=A, b=B", tags="angle sum property triangle exterior angle",
  steps="Draw a line through the top vertex parallel to the base | Alternate angles equal the two base angles | The three angles on the straight line add to 180°", ask="C")

X("m9-chord", 9, M, "Circles", "Chord and its distance from the centre", "concept",
  "The perpendicular from the centre bisects the chord.",
  params="r:Radius:cm:13:1:50; d:Distance of chord from centre:cm:5:0:49",
  out="L:Chord length:cm:2*sqrt(r**2 - d**2); th:Angle subtended at the centre:deg:2*acos(d/r)*180/pi",
  plot="d=0..r: L", eqs="L = 2*sqrt(r**2 - d**2)", scene="shape: kind=circle_chord, a=r, b=d", tags="chord circle perpendicular bisector distance centre",
  steps="The perpendicular from the centre to a chord bisects it | In the right triangle: (L/2)² + d² = r² | So L = 2√(r² − d²)", ask="L")

X("m9-parallelogram", 9, M, "Quadrilaterals", "Area of a parallelogram and a trapezium", "concept",
  "Base times height, and half the sum of parallel sides times height.",
  params="b1:Base (or parallel side 1):cm:10:1:50; b2:Parallel side 2:cm:6:1:50; h:Height:cm:4:1:50",
  out="A_par:Parallelogram area:cm^2:b1*h; A_trap:Trapezium area:cm^2:(b1 + b2)*h/2", eqs="A_par = b1*h | A_trap = (b1 + b2)*h/2",
  tags="area parallelogram trapezium height base",
  steps="Cut the triangle off one end of a parallelogram and move it to the other: a rectangle b × h | Two copies of a trapezium make a parallelogram with base b1 + b2 | So the trapezium is half of that", ask="A_trap")

X("m9-mean", 9, M, "Statistics", "Mean of an arithmetic sequence of marks", "concept",
  "Mean, and how adding a constant or scaling changes it.",
  params="first:First value:-:40:0:100; step:Common step:-:5:0:20; n:Number of values:-:10:1:50:1",
  out="mean:Mean:-:first + (n - 1)*step/2; median:Median:-:first + (n - 1)*step/2; total:Sum:-:n*(2*first + (n - 1)*step)/2",
  eqs="mean = total/n", tags="mean median statistics average",
  steps="Mean = sum of values / number of values | For evenly spaced values the sum is n × (first + last)/2 | So the mean is the average of the first and last value", ask="mean")

# ================================================================ Class 10
X("m10-quadratic", 10, M, "Quadratic Equations", "Quadratic formula and the discriminant", "derivation",
  "Roots of ax² + bx + c = 0 and what the discriminant says.",
  params="a:a:-:1:-5:5; b:b:-:-5:-20:20; c:c:-:6:-20:20",
  out="D:Discriminant:-:b**2 - 4*a*c; x1:Root 1:-:(-b + sqrt(b**2 - 4*a*c))/(2*a); x2:Root 2:-:(-b - sqrt(b**2 - 4*a*c))/(2*a); xv:Vertex x:-:-b/(2*a)",
  series="y:y:-:a*x**2 + b*x + c", plot="x=-10..10: y", eqs="x = (-b + sqrt(b**2 - 4*a*c))/(2*a) | D = b**2 - 4*a*c",
  scene="graph", tags="quadratic formula discriminant roots nature of roots completing the square", lab="grapher",
  steps="Divide by a: x² + (b/a)x + c/a = 0 | Complete the square: (x + b/2a)² = (b² − 4ac)/4a² | Take square roots: x = (−b ± √(b² − 4ac))/2a | D > 0: two real roots, D = 0: equal roots, D < 0: no real roots", ask="x1,D")

X("m10-zeros", 10, M, "Polynomials", "Zeros and coefficients of a quadratic", "concept",
  "Sum and product of zeros.",
  params="a:a:-:2:-5:5; b:b:-:-8:-20:20; c:c:-:6:-20:20",
  out="s:Sum of zeros:-:-b/a; p:Product of zeros:-:c/a", eqs="s = -b/a | p = c/a", tags="zeros coefficients relationship sum product polynomial",
  steps="If α and β are zeros, ax² + bx + c = a(x − α)(x − β) | Expand: a x² − a(α + β)x + aαβ | Compare coefficients: α + β = −b/a, αβ = c/a", ask="s,p")

X("m10-linear-pair", 10, M, "Pair of Linear Equations in Two Variables", "Solving a pair of linear equations", "graph",
  "Where two lines meet, both equations are true.",
  params="a1:a₁:-:2:-10:10; b1:b₁:-:3:-10:10; c1:c₁:-:12:-30:30; a2:a₂:-:1:-10:10; b2:b₂:-:-1:-10:10; c2:c₂:-:1:-30:30",
  out="x:x:-:(c1*b2 - c2*b1)/(a1*b2 - a2*b1); y:y:-:(a1*c2 - a2*c1)/(a1*b2 - a2*b1); det:a₁b₂ − a₂b₁:-:a1*b2 - a2*b1",
  series="y1:Line 1:-:(c1 - a1*xx)/b1; y2:Line 2:-:(c2 - a2*xx)/b2", plot="xx=-10..10: y1, y2",
  eqs="a1*x + b1*y = c1 | a2*x + b2*y = c2", scene="graph", tags="pair of linear equations cross multiplication elimination substitution consistent",
  steps="Multiply to make the y coefficients equal and subtract | x = (c₁b₂ − c₂b₁)/(a₁b₂ − a₂b₁) | Similarly y = (a₁c₂ − a₂c₁)/(a₁b₂ − a₂b₁) | If a₁b₂ − a₂b₁ = 0 the lines are parallel or the same", ask="x,y")

X("m10-ap", 10, M, "Arithmetic Progressions", "nth term and sum of an AP", "derivation",
  "aₙ = a + (n − 1)d and Sₙ = n/2 (2a + (n − 1)d).",
  params="a:First term:-:3:-50:50; d:Common difference:-:4:-20:20; n:Number of terms:-:10:1:100:1",
  out="an:nth term:-:a + (n - 1)*d; Sn:Sum of n terms:-:n*(2*a + (n - 1)*d)/2", plot="n: an, Sn",
  eqs="an = a + (n - 1)*d | Sn = n*(2*a + (n - 1)*d)/2", tags="arithmetic progression nth term sum ap",
  steps="Each term adds d, so the nth term is a + (n − 1)d | Write Sₙ forwards and backwards and add: each pair sums to 2a + (n − 1)d | There are n pairs, so 2Sₙ = n(2a + (n − 1)d)", ask="an,Sn")

X("m10-distance", 10, M, "Coordinate Geometry", "Distance formula", "derivation",
  "Pythagoras on the coordinate plane.",
  params="x1:x₁:-:1:-20:20; y1:y₁:-:2:-20:20; x2:x₂:-:7:-20:20; y2:y₂:-:10:-20:20",
  out="d:Distance:-:sqrt((x2 - x1)**2 + (y2 - y1)**2); mx:Midpoint x:-:(x1 + x2)/2; my:Midpoint y:-:(y1 + y2)/2",
  eqs="d = sqrt((x2 - x1)**2 + (y2 - y1)**2)", tags="distance formula coordinate geometry midpoint",
  steps="Draw a right triangle with legs x₂ − x₁ and y₂ − y₁ | The distance is the hypotenuse | d = √((x₂ − x₁)² + (y₂ − y₁)²)", ask="d")

X("m10-section", 10, M, "Coordinate Geometry", "Section formula", "concept",
  "The point dividing a segment in the ratio m : n.",
  params="x1:x₁:-:-2:-20:20; y1:y₁:-:3:-20:20; x2:x₂:-:8:-20:20; y2:y₂:-:-7:-20:20; m:m:-:2:0.1:10; n:n:-:3:0.1:10",
  out="px:x of dividing point:-:(m*x2 + n*x1)/(m + n); py:y of dividing point:-:(m*y2 + n*y1)/(m + n)",
  eqs="px = (m*x2 + n*x1)/(m + n) | py = (m*y2 + n*y1)/(m + n)", tags="section formula ratio internal division",
  steps="Similar triangles along the segment give (px − x₁)/(x₂ − px) = m/n | Solve for px | The same for y", ask="px,py")

X("m10-triangle-area", 10, M, "Coordinate Geometry", "Area of a triangle from its vertices", "concept",
  "Zero area means the points are collinear.",
  params="x1:x₁:-:1:-20:20; y1:y₁:-:1:-20:20; x2:x₂:-:5:-20:20; y2:y₂:-:2:-20:20; x3:x₃:-:3:-20:20; y3:y₃:-:6:-20:20",
  out="A:Area:-:Abs(x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2))/2", eqs="A = Abs(x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2))/2",
  tags="area of triangle coordinates vertices collinear",
  steps="Drop perpendiculars to the x-axis to form trapeziums | Add and subtract their areas | The result is ½|x₁(y₂ − y₃) + x₂(y₃ − y₁) + x₃(y₁ − y₂)|", ask="A")

X("m10-trig-ratios", 10, M, "Introduction to Trigonometry", "Trigonometric ratios", "graph",
  "sin, cos and tan of an angle, and sin² + cos² = 1.",
  params="th:Angle:deg:30:0:90",
  out="sn:sin θ:-:sin(th*pi/180); cs:cos θ:-:cos(th*pi/180); tn:tan θ:-:tan(th*pi/180); check:sin²θ + cos²θ:-:sin(th*pi/180)**2 + cos(th*pi/180)**2",
  plot="th: sn, cs", eqs="sin(th)**2 + cos(th)**2 = 1 | tn = sn/cs", scene="vector: A=1, B=0, th=th", tags="trigonometric ratios sin cos tan identity",
  steps="In a right triangle with angle θ: sin θ = opposite/hypotenuse, cos θ = adjacent/hypotenuse | tan θ = sin θ / cos θ | Pythagoras gives sin²θ + cos²θ = 1", lab="unitcircle", ask="sn,cs")

X("m10-heights", 10, M, "Some Applications of Trigonometry", "Height of a tower", "concept",
  "Angle of elevation and distance give the height.",
  params="d:Distance from the foot:m:30:1:500; th:Angle of elevation:deg:60:1:89; eye:Observer's eye height:m:1.5:0:3",
  out="h:Height of the tower:m:d*tan(th*pi/180) + eye; los:Line of sight length:m:d/cos(th*pi/180)", plot="th: h",
  eqs="h = d*tan(th) + eye", scene="shape: kind=tower, a=d, b=th", tags="heights and distances angle of elevation tower",
  steps="The tower, the ground and the line of sight make a right triangle | tan θ = (h − eye height)/d | So h = d tan θ + eye height", ask="h")

X("m10-two-angles", 10, M, "Some Applications of Trigonometry", "Height from two angles of elevation", "derivation",
  "Walking towards a tower: two angles and the distance walked.",
  params="al:First angle (farther):deg:30:1:88; be:Second angle (nearer):deg:60:2:89; d:Distance walked:m:40:1:500",
  out="h:Height:m:d*tan(al*pi/180)*tan(be*pi/180)/(tan(be*pi/180) - tan(al*pi/180)); x:Distance of the nearer point from the foot:m:d*tan(al*pi/180)/(tan(be*pi/180) - tan(al*pi/180))",
  eqs="h = d*tan(al)*tan(be)/(tan(be) - tan(al))", tags="heights distances two angles of elevation", ask="h",
  steps="From the nearer point: h = x tan β | From the farther point: h = (x + d) tan α | Equate and solve for x = d tan α/(tan β − tan α) | Then h = d tan α tan β/(tan β − tan α)")

X("m10-tangent", 10, M, "Circles", "Length of a tangent", "concept",
  "The tangent is perpendicular to the radius.",
  params="r:Radius:cm:5:0.5:50; d:Distance of point from centre:cm:13:1:100",
  out="t:Tangent length:cm:sqrt(d**2 - r**2); th:Angle between the two tangents:deg:2*asin(r/d)*180/pi",
  eqs="t = sqrt(d**2 - r**2)", tags="tangent length circle external point perpendicular radius",
  steps="The radius to the point of contact is perpendicular to the tangent | The centre, the point and the contact point form a right triangle | t² + r² = d²", ask="t")

X("m10-sector", 10, M, "Areas Related to Circles", "Sector and segment of a circle", "concept",
  "Area and arc length of a slice of a circle.",
  params="r:Radius:cm:21:1:100; th:Angle of the sector:deg:60:1:360",
  out="A_sec:Sector area:cm^2:th/360*pi*r**2; arc:Arc length:cm:th/360*2*pi*r; A_seg:Minor segment area:cm^2:th/360*pi*r**2 - r**2*sin(th*pi/180)/2",
  plot="th: A_sec", eqs="A_sec = th/360*pi*r**2 | arc = th/360*2*pi*r", scene="shape: kind=sector, a=r, b=th", tags="sector segment arc length area circle",
  steps="A sector with angle θ is θ/360 of the whole circle | Its area is (θ/360)πr² and its arc (θ/360)2πr | Segment = sector − triangle, and the triangle is ½r² sin θ", ask="A_sec,arc")

X("m10-frustum", 10, M, "Surface Areas and Volumes", "Frustum of a cone", "concept",
  "A bucket shape: volume and curved surface.", boards=ICSE,
  params="R:Larger radius:cm:20:1:50; r:Smaller radius:cm:8:0.5:50; h:Height:cm:16:1:100",
  out="l:Slant height:cm:sqrt(h**2 + (R - r)**2); V:Volume:cm^3:pi*h*(R**2 + r**2 + R*r)/3; CSA:Curved surface area:cm^2:pi*(R + r)*sqrt(h**2 + (R - r)**2)",
  eqs="V = pi*h*(R**2 + r**2 + R*r)/3", tags="frustum cone bucket volume surface area", ask="V",
  steps="A frustum is a big cone with a small cone cut off the top | Subtract the volumes and use similar triangles | V = πh(R² + r² + Rr)/3")

X("m10-combined", 10, M, "Surface Areas and Volumes", "Combined solid: cone on a hemisphere", "concept",
  "An ice cream or a toy top.",
  params="r:Common radius:cm:3.5:0.5:20; h:Height of the cone:cm:10:0.5:50",
  out="V:Total volume:cm^3:pi*r**2*h/3 + 2*pi*r**3/3; SA:Outer surface area:cm^2:pi*r*sqrt(r**2 + h**2) + 2*pi*r**2",
  eqs="V = pi*r**2*h/3 + 2*pi*r**3/3", tags="combination of solids cone hemisphere toy volume", ask="V",
  steps="The volumes simply add: cone ⅓πr²h + hemisphere ⅔πr³ | For the surface, only the outer faces count: the cone's curved surface and the hemisphere's curved surface")

X("m10-dice", 10, M, "Probability", "Sum of two dice", "concept",
  "Why 7 is the most likely total.",
  params="S:Target sum:-:7:2:12:1",
  out="ways:Favourable outcomes:-:6 - Abs(S - 7); P:Probability:-:(6 - Abs(S - 7))/36", plot="S: P", eqs="P = ways/36",
  tags="probability dice sum outcomes", lab="probability",
  steps="Two dice give 6 × 6 = 36 equally likely outcomes | Count pairs adding to S: 1 way for 2, rising to 6 ways for 7, then falling | P = favourable/36", ask="P")

X("m10-probability", 10, M, "Probability", "Classical probability", "concept",
  "Drawing a card, picking a ball: favourable over total.",
  params="fav:Favourable outcomes:-:13:0:100:1; total:Total outcomes:-:52:1:200:1",
  out="P:Probability:-:fav/total; Pnot:Probability of not happening:-:1 - fav/total", eqs="P = fav/total | Pnot = 1 - P",
  tags="probability complementary events cards balls",
  steps="When all outcomes are equally likely, P(E) = favourable outcomes / total outcomes | P(not E) = 1 − P(E)", ask="P")

X("m10-mode", 10, M, "Statistics", "Mode of grouped data", "concept",
  "Estimating the most frequent value from a frequency table.",
  params="l:Lower limit of modal class:-:40:0:100; h:Class width:-:10:1:50; f1:Frequency of modal class:-:12:1:100:1; f0:Frequency of class before:-:8:0:100:1; f2:Frequency of class after:-:6:0:100:1",
  out="mode:Mode:-:l + (f1 - f0)/(2*f1 - f0 - f2)*h", eqs="mode = l + (f1 - f0)/(2*f1 - f0 - f2)*h", tags="mode grouped data statistics modal class",
  steps="Find the modal class, the one with the highest frequency | Use mode = l + (f₁ − f₀)/(2f₁ − f₀ − f₂) × h | The formula places the mode closer to the larger neighbouring class", ask="mode")

X("m10-median", 10, M, "Statistics", "Median of grouped data", "concept",
  "The middle value from a cumulative frequency table.",
  params="l:Lower limit of median class:-:30:0:100; h:Class width:-:10:1:50; n:Total frequency:-:50:2:500:1; cf:Cumulative frequency before:-:18:0:500:1; f:Frequency of median class:-:12:1:200:1",
  out="median:Median:-:l + (n/2 - cf)/f*h", eqs="median = l + (n/2 - cf)/f*h", tags="median grouped data cumulative frequency ogive",
  steps="Find the class where the cumulative frequency passes n/2 | Assume values are spread evenly inside it | median = l + (n/2 − cf)/f × h", ask="median")

X("m10-recurring-deposit", 10, M, "Banking", "Recurring deposit account", "concept",
  "Monthly savings: interest and maturity value.", boards=ICSE,
  params="P:Monthly instalment:rupees:1000:100:50000; n:Number of months:-:24:1:120:1; r:Rate of interest:% p.a.:7:1:15",
  out="I:Interest:rupees:P*n*(n + 1)/(2*12)*r/100; MV:Maturity value:rupees:P*n + P*n*(n + 1)/(2*12)*r/100",
  plot="n: MV", eqs="I = P*n*(n + 1)/24*r/100", tags="recurring deposit banking interest maturity value",
  steps="The first instalment earns interest for n months, the last for 1 month | Total 'money months' = P(1 + 2 + … + n) = Pn(n + 1)/2 | Interest = that × r/100 × 1/12 | Maturity value = Pn + I", ask="MV")

X("m10-compound", 10, M, "Compound Interest", "Compound interest", "concept",
  "Interest on interest.", boards=ICSE,
  params="P:Principal:rupees:10000:100:1000000; r:Rate:% p.a.:8:1:20; n:Years:-:3:1:30:1",
  out="A:Amount:rupees:P*(1 + r/100)**n; CI:Compound interest:rupees:P*(1 + r/100)**n - P; SI:Simple interest for comparison:rupees:P*r*n/100",
  plot="n: A", eqs="A = P*(1 + r/100)**n", tags="compound interest simple interest amount principal growth",
  steps="Each year the amount is multiplied by (1 + r/100) | After n years A = P(1 + r/100)ⁿ | Compound interest = A − P", ask="A,CI")

# ================================================================ Class 11
X("m11-radian", 11, M, "Trigonometric Functions", "Radian measure and arc length", "concept",
  "s = rθ when θ is in radians.",
  params="r:Radius:cm:10:1:100; deg:Angle:deg:60:0:360",
  out="rad:Angle in radians:rad:deg*pi/180; s:Arc length:cm:r*deg*pi/180", plot="deg: rad", eqs="s = r*rad | rad = deg*pi/180",
  tags="radian degree conversion arc length",
  steps="A radian is the angle for which the arc equals the radius | A full turn is 2π radians = 360° | So θ(rad) = θ(deg) × π/180 and s = rθ", lab="unitcircle", ask="rad,s")

X("m11-sine-graph", 11, M, "Trigonometric Functions", "Graph of y = A sin(Bx + C) + D", "graph",
  "Amplitude, period, phase shift and vertical shift.",
  params="A:Amplitude A:-:2:-5:5; B:Frequency B:-:1:0.1:5; C:Phase C:rad:0:-3.14:3.14; D:Vertical shift D:-:0:-5:5",
  out="period:Period:-:2*pi/B; shift:Phase shift:-:-C/B; ymax:Maximum:-:Abs(A) + D; ymin:Minimum:-:D - Abs(A)",
  series="y:y:-:A*sin(B*x + C) + D", plot="x=0..4*pi: y", eqs="y = A*sin(B*x + C) + D | period = 2*pi/B", scene="graph",
  tags="trigonometric graph sine amplitude period phase shift transformation", lab="unitcircle",
  steps="sin repeats every 2π, so sin(Bx) repeats when Bx grows by 2π: period 2π/B | A stretches it vertically | Bx + C = 0 at x = −C/B: the phase shift | D moves the whole graph up", ask="period")

X("m11-compound-angle", 11, M, "Trigonometric Functions", "sin(A + B) and cos(A + B)", "derivation",
  "Check the addition formulas for any two angles.",
  params="A:Angle A:deg:30:0:180; B:Angle B:deg:45:0:180",
  out="lhs:sin(A + B):-:sin((A + B)*pi/180); rhs:sin A cos B + cos A sin B:-:sin(A*pi/180)*cos(B*pi/180) + cos(A*pi/180)*sin(B*pi/180); cosAB:cos(A + B):-:cos((A + B)*pi/180)",
  eqs="sin(A + B) = sin(A)*cos(B) + cos(A)*sin(B) | cos(A + B) = cos(A)*cos(B) - sin(A)*sin(B)", tags="compound angle addition formula sin cos",
  steps="Place two unit vectors at angles A and −B on the unit circle | The chord between them has the same length as the chord from angle A + B to angle 0 | Squaring the distance formula for both chords gives cos(A + B) = cos A cos B − sin A sin B | Replace A by 90° − A to get the sine formula", ask="lhs")

X("m11-complex", 11, M, "Complex Numbers and Quadratic Equations", "Modulus and argument of a complex number", "concept",
  "z = x + iy on the Argand plane.",
  params="x:Real part:-:3:-10:10; y:Imaginary part:-:4:-10:10",
  out="r:Modulus |z|:-:sqrt(x**2 + y**2); arg:Argument:deg:atan2(y, x)*180/pi", eqs="r = sqrt(x**2 + y**2) | tan(arg) = y/x",
  scene="vector: A=x, B=y, th=90", tags="complex number modulus argument argand polar form", lab="complex",
  steps="Plot z as the point (x, y) | Its distance from the origin is |z| = √(x² + y²) | The angle from the positive real axis is the argument; use the quadrant of (x, y)", ask="r,arg")

X("m11-de-moivre", 11, M, "Complex Numbers and Quadratic Equations", "Powers of a complex number", "concept",
  "(r cis θ)ⁿ = rⁿ cis nθ.",
  params="r:Modulus:-:1.2:0.1:3; th:Argument:deg:30:-180:180; n:Power:-:4:1:10:1",
  out="rn:Modulus of zⁿ:-:r**n; argn:Argument of zⁿ:deg:n*th; re:Real part:-:r**n*cos(n*th*pi/180); im:Imaginary part:-:r**n*sin(n*th*pi/180)",
  eqs="rn = r**n | argn = n*th", tags="de moivre theorem powers complex polar form", lab="complex",
  steps="Multiplying complex numbers multiplies moduli and adds arguments | So zⁿ has modulus rⁿ and argument nθ", ask="rn,argn")

X("m11-perm-comb", 11, M, "Permutations and Combinations", "Permutations and combinations", "concept",
  "Arrangements when order matters, and selections when it doesn't.",
  params="n:n (objects):-:8:1:20:1; r:r (chosen):-:3:0:20:1",
  out="nPr:Permutations nPr:-:factorial(n)/factorial(n - r); nCr:Combinations nCr:-:factorial(n)/(factorial(r)*factorial(n - r))",
  eqs="nPr = factorial(n)/factorial(n - r) | nCr = nPr/factorial(r)", tags="permutation combination factorial arrangements selections",
  steps="First place: n choices, second: n − 1, … r places: n(n − 1)…(n − r + 1) = n!/(n − r)! | Each selection of r objects can be arranged in r! ways | So nCr = nPr / r!", ask="nPr,nCr")

X("m11-binomial", 11, M, "Binomial Theorem", "General term of (a + b)ⁿ", "concept",
  "The (r + 1)th term of a binomial expansion.",
  params="a:a:-:2:-5:5; b:b:-:1:-5:5; n:n:-:6:1:15:1; r:r:-:2:0:15:1",
  out="T:Term T(r+1):-:factorial(n)/(factorial(r)*factorial(n - r))*a**(n - r)*b**r; total:Whole expansion (a + b)ⁿ:-:(a + b)**n",
  eqs="T = binomial(n, r)*a**(n - r)*b**r", tags="binomial theorem general term expansion pascal triangle",
  steps="(a + b)ⁿ is the product of n brackets | A term with bʳ picks b from r brackets and a from the other n − r | There are nCr ways to choose them | So T(r+1) = nCr aⁿ⁻ʳ bʳ", ask="T")

X("m11-gp", 11, M, "Sequences and Series", "Geometric progression", "derivation",
  "nth term and sum of a GP.",
  params="a:First term:-:2:-20:20; r:Common ratio:-:3:-3:3; n:Number of terms:-:6:1:30:1",
  out="an:nth term:-:a*r**(n - 1); Sn:Sum of n terms:-:a*(r**n - 1)/(r - 1); Sinf:Sum to infinity (if |r| < 1):-:a/(1 - r)",
  plot="n: an", eqs="an = a*r**(n - 1) | Sn = a*(r**n - 1)/(r - 1)", tags="geometric progression nth term sum infinite series",
  steps="Each term multiplies by r: aₙ = arⁿ⁻¹ | Write Sₙ and rSₙ and subtract: (r − 1)Sₙ = a(rⁿ − 1) | For |r| < 1, rⁿ → 0 and S∞ = a/(1 − r)", ask="an,Sn")

X("m11-means", 11, M, "Sequences and Series", "Arithmetic, geometric and harmonic means", "concept",
  "AM ≥ GM ≥ HM for any two positive numbers.",
  params="a:a:-:4:0.1:100; b:b:-:16:0.1:100",
  out="AM:Arithmetic mean:-:(a + b)/2; GM:Geometric mean:-:sqrt(a*b); HM:Harmonic mean:-:2*a*b/(a + b)", plot="b: AM, GM, HM",
  eqs="AM = (a + b)/2 | GM = sqrt(a*b) | GM**2 = AM*HM", tags="arithmetic mean geometric mean harmonic mean inequality",
  steps="AM − GM = ½(√a − √b)² ≥ 0 | GM² = ab = AM × HM | So AM ≥ GM ≥ HM, with equality only when a = b", ask="GM")

X("m11-line", 11, M, "Straight Lines", "Slope and equation of a line", "graph",
  "Line through two points: slope, angle and intercept.",
  params="x1:x₁:-:1:-10:10; y1:y₁:-:2:-10:10; x2:x₂:-:4:-10:10; y2:y₂:-:8:-10:10",
  out="m:Slope:-:(y2 - y1)/(x2 - x1); ang:Inclination:deg:atan((y2 - y1)/(x2 - x1))*180/pi; c:y-intercept:-:y1 - (y2 - y1)/(x2 - x1)*x1",
  series="y:y:-:y1 + (y2 - y1)/(x2 - x1)*(x - x1)", plot="x=-10..10: y", eqs="m = (y2 - y1)/(x2 - x1) | y = m*x + c",
  scene="graph", tags="straight line slope intercept two point form inclination",
  steps="Slope = rise/run = (y₂ − y₁)/(x₂ − x₁) = tan θ | Point-slope form: y − y₁ = m(x − x₁) | Rearranged: y = mx + c", ask="m,c")

X("m11-point-line", 11, M, "Straight Lines", "Distance of a point from a line", "derivation",
  "Shortest distance from (x₀, y₀) to Ax + By + C = 0.",
  params="A:A:-:3:-10:10; B:B:-:4:-10:10; C:C:-:-12:-30:30; x0:x₀:-:5:-10:10; y0:y₀:-:6:-10:10",
  out="d:Distance:-:Abs(A*x0 + B*y0 + C)/sqrt(A**2 + B**2)", eqs="d = Abs(A*x0 + B*y0 + C)/sqrt(A**2 + B**2)",
  tags="distance point line perpendicular",
  steps="The perpendicular from the point meets the line where the triangle formed with the axes intercepts has a known area | Area = ½ × base × height in two ways | Solving gives d = |Ax₀ + By₀ + C|/√(A² + B²)", ask="d")

X("m11-circle", 11, M, "Conic Sections", "Equation of a circle", "graph",
  "(x − h)² + (y − k)² = r².",
  params="h:Centre x:-:1:-10:10; k:Centre y:-:-2:-10:10; r:Radius:-:4:0.5:10",
  out="area:Area:-:pi*r**2; circ:Circumference:-:2*pi*r; D:Coefficient D in x² + y² + Dx + Ey + F = 0:-:-2*h; F:Constant F:-:h**2 + k**2 - r**2",
  series="x:x:-:h + r*cos(t); y:y:-:k + r*sin(t)", plot="t=0..2*pi: x ~ y", eqs="(x - h)**2 + (y - k)**2 = r**2",
  scene="graph", tags="circle equation centre radius general form", lab="conics",
  steps="A point (x, y) is on the circle when its distance from (h, k) equals r | Square the distance formula | Expanding gives the general form x² + y² + Dx + Ey + F = 0", ask="F")

X("m11-parabola", 11, M, "Conic Sections", "Parabola y² = 4ax", "graph",
  "Focus, directrix and latus rectum.",
  params="a:a:-:2:0.2:10",
  out="focus:Focus x:-:a; directrix:Directrix x:-:-a; LR:Latus rectum length:-:4*a",
  series="x:x:-:a*t**2; y:y:-:2*a*t", plot="t=-3..3: x ~ y", eqs="y**2 = 4*a*x", scene="graph", tags="parabola focus directrix latus rectum conic", lab="conics",
  steps="A parabola is the set of points equidistant from the focus (a, 0) and the line x = −a | √((x − a)² + y²) = x + a | Squaring gives y² = 4ax | Latus rectum: at x = a, y = ±2a, length 4a", ask="LR")

X("m11-ellipse", 11, M, "Conic Sections", "Ellipse", "graph",
  "x²/a² + y²/b² = 1: eccentricity and foci.",
  params="a:Semi-major axis a:-:5:1:10; b:Semi-minor axis b:-:3:0.5:10",
  out="e:Eccentricity:-:sqrt(1 - b**2/a**2); c:Focus distance:-:sqrt(a**2 - b**2); LR:Latus rectum:-:2*b**2/a; area:Area:-:pi*a*b",
  series="x:x:-:a*cos(t); y:y:-:b*sin(t)", plot="t=0..2*pi: x ~ y", eqs="x**2/a**2 + y**2/b**2 = 1 | e = sqrt(1 - b**2/a**2)",
  scene="graph", tags="ellipse eccentricity foci latus rectum conic", lab="conics",
  steps="The sum of distances to the two foci is 2a | The foci are at (±c, 0) with c² = a² − b² | Eccentricity e = c/a < 1", ask="e,c")

X("m11-hyperbola", 11, M, "Conic Sections", "Hyperbola", "graph",
  "x²/a² − y²/b² = 1: eccentricity and asymptotes.",
  params="a:a:-:3:0.5:10; b:b:-:4:0.5:10",
  out="e:Eccentricity:-:sqrt(1 + b**2/a**2); c:Focus distance:-:sqrt(a**2 + b**2); slope:Asymptote slope:-:b/a",
  series="x:x:-:a*cosh(t); y:y:-:b*sinh(t)", plot="t=-2..2: x ~ y", eqs="x**2/a**2 - y**2/b**2 = 1 | e = sqrt(1 + b**2/a**2)",
  scene="graph", tags="hyperbola eccentricity asymptotes conic", lab="conics",
  steps="The difference of distances to the foci is 2a | c² = a² + b², so e = c/a > 1 | For large x the curve approaches the lines y = ±(b/a)x", ask="e")

X("m11-3d-distance", 11, M, "Introduction to Three Dimensional Geometry", "Distance between two points in space", "concept",
  "Pythagoras in three dimensions.",
  params="x1:x₁:-:1:-10:10; y1:y₁:-:2:-10:10; z1:z₁:-:3:-10:10; x2:x₂:-:4:-10:10; y2:y₂:-:6:-10:10; z2:z₂:-:15:-10:20",
  out="d:Distance:-:sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)", eqs="d = sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)",
  tags="3d distance formula coordinates space",
  steps="Across the base: the distance in the xy-plane is √(Δx² + Δy²) | Then up by Δz at right angles | d = √(Δx² + Δy² + Δz²)", ask="d")

X("m11-limit", 11, M, "Limits and Derivatives", "The limit of sin x / x", "graph",
  "Why sin x / x approaches 1 as x approaches 0.",
  params="x0:x close to 0:rad:0.1:0.001:1.5",
  out="val:sin(x)/x:-:sin(x0)/x0; err:Difference from 1:-:1 - sin(x0)/x0", series="y:sin(x)/x:-:sin(x)/x", plot="x=-10..10: y",
  eqs="lim = sin(x)/x", scene="graph", tags="limit sin x over x standard limit squeeze",
  steps="For 0 < x < π/2 compare areas: triangle ≤ sector ≤ larger triangle | ½ sin x ≤ ½ x ≤ ½ tan x | Divide by ½ sin x and flip: cos x ≤ sin x / x ≤ 1 | As x → 0, cos x → 1, so the limit is 1", ask="val")

X("m11-first-principle", 11, M, "Limits and Derivatives", "Derivative from first principles", "derivation",
  "The slope of a secant becomes the slope of the tangent.",
  params="n:Power n in f(x) = xⁿ:-:3:1:6:1; a:Point a:-:2:0.1:5; h:Step h:-:0.5:0.001:2",
  out="secant:Secant slope ((a + h)ⁿ − aⁿ)/h:-:((a + h)**n - a**n)/h; exact:Derivative n aⁿ⁻¹:-:n*a**(n - 1); gap:Difference:-:((a + h)**n - a**n)/h - n*a**(n - 1)",
  plot="h: secant", eqs="f_prime = lim(((a + h)**n - a**n)/h) | f_prime = n*a**(n - 1)", tags="derivative first principles limit secant tangent power rule",
  steps="The secant through x = a and x = a + h has slope (f(a + h) − f(a))/h | Expand (a + h)ⁿ with the binomial theorem | Every term after naⁿ⁻¹h has h² or more | Divide by h and let h → 0: f′(a) = naⁿ⁻¹", lab="grapher", ask="secant")

X("m11-variance", 11, M, "Statistics", "Mean and variance of the first n natural numbers", "concept",
  "A formula check: variance (n² − 1)/12.",
  params="n:n:-:10:2:100:1",
  out="mean:Mean:-:(n + 1)/2; var:Variance:-:(n**2 - 1)/12; sd:Standard deviation:-:sqrt((n**2 - 1)/12)", plot="n: sd",
  eqs="var = (n**2 - 1)/12", tags="variance standard deviation natural numbers statistics",
  steps="Mean = (n + 1)/2 | Mean of squares = (n + 1)(2n + 1)/6 | Variance = mean of squares − (mean)² = (n² − 1)/12", ask="var")

X("m11-prob-union", 11, M, "Probability", "Probability of A or B", "law",
  "Addition rule for two events.",
  params="PA:P(A):-:0.5:0:1; PB:P(B):-:0.4:0:1; PAB:P(A and B):-:0.2:0:1",
  out="PAorB:P(A or B):-:PA + PB - PAB; PnotA:P(not A):-:1 - PA", eqs="PAorB = PA + PB - PAB", tags="probability addition rule union intersection events",
  steps="Adding P(A) and P(B) counts the overlap twice | Subtract it once | P(A ∪ B) = P(A) + P(B) − P(A ∩ B)", ask="PAorB")

X("m11-sets", 11, M, "Sets", "Counting with a Venn diagram", "concept",
  "n(A ∪ B) = n(A) + n(B) − n(A ∩ B).",
  params="nA:Students who like A:-:40:0:200:1; nB:Students who like B:-:30:0:200:1; nAB:Like both:-:12:0:200:1",
  out="nAorB:Like at least one:-:nA + nB - nAB; onlyA:Only A:-:nA - nAB; onlyB:Only B:-:nB - nAB", eqs="nAorB = nA + nB - nAB",
  tags="sets venn diagram union intersection counting", ask="nAorB",
  steps="Everyone in the overlap is counted in both n(A) and n(B) | Subtract n(A ∩ B) once | Only A = n(A) − n(A ∩ B)")

# ================================================================ Class 12
X("m12-inverse-trig", 12, M, "Inverse Trigonometric Functions", "Principal values of sin⁻¹, cos⁻¹ and tan⁻¹", "graph",
  "Which angle has this sine?",
  params="x:x:-:0.5:-1:1",
  out="asn:sin⁻¹ x:deg:asin(x)*180/pi; acs:cos⁻¹ x:deg:acos(x)*180/pi; atn:tan⁻¹ x:deg:atan(x)*180/pi; check:sin⁻¹ x + cos⁻¹ x:deg:(asin(x) + acos(x))*180/pi",
  plot="x: asn, acs", eqs="asin(x) + acos(x) = pi/2", tags="inverse trigonometric principal value branch",
  steps="sin is one-to-one only on [−90°, 90°], so sin⁻¹ takes values there | cos⁻¹ takes values in [0°, 180°] | Their sum is always 90°", ask="asn")

X("m12-det", 12, M, "Determinants", "Determinant of a 2 × 2 and 3 × 3 matrix", "concept",
  "How a matrix scales area.",
  params="a:a₁₁:-:2:-10:10; b:a₁₂:-:1:-10:10; c:a₂₁:-:3:-10:10; d:a₂₂:-:4:-10:10; e:a₃₃ (third row is 0 0 e):-:2:-10:10",
  out="D2:2 × 2 determinant:-:a*d - b*c; D3:3 × 3 determinant:-:e*(a*d - b*c)", eqs="D2 = a*d - b*c",
  tags="determinant matrix area scaling", lab="transform",
  steps="For [[a, b], [c, d]], det = ad − bc | It is the factor by which the matrix scales areas | Expanding a 3 × 3 along the last row 0, 0, e gives e(ad − bc)", ask="D2")

X("m12-inverse-2x2", 12, M, "Matrices", "Inverse of a 2 × 2 matrix", "concept",
  "Swap, change signs, divide by the determinant.",
  params="a:a:-:4:-10:10; b:b:-:7:-10:10; c:c:-:2:-10:10; d:d:-:6:-10:10",
  out="det:Determinant:-:a*d - b*c; i11:Inverse (1,1):-:d/(a*d - b*c); i12:Inverse (1,2):-:-b/(a*d - b*c); i21:Inverse (2,1):-:-c/(a*d - b*c); i22:Inverse (2,2):-:a/(a*d - b*c)",
  eqs="i11 = d/det | det = a*d - b*c", tags="inverse matrix adjoint determinant",
  steps="A⁻¹ = adj A / |A| | For a 2 × 2 matrix the adjoint swaps a and d and negates b and c | If |A| = 0 there is no inverse", ask="det,i11")

X("m12-cramer", 12, M, "Determinants", "Cramer's rule", "concept",
  "Solving two equations with determinants.",
  params="a1:a₁:-:2:-10:10; b1:b₁:-:1:-10:10; c1:c₁:-:5:-30:30; a2:a₂:-:1:-10:10; b2:b₂:-:3:-10:10; c2:c₂:-:10:-30:30",
  out="D:D:-:a1*b2 - a2*b1; Dx:D_x:-:c1*b2 - c2*b1; Dy:D_y:-:a1*c2 - a2*c1; x:x:-:(c1*b2 - c2*b1)/(a1*b2 - a2*b1); y:y:-:(a1*c2 - a2*c1)/(a1*b2 - a2*b1)",
  eqs="x = Dx/D | y = Dy/D", tags="cramer rule determinants system of equations", ask="x,y",
  steps="D is the determinant of the coefficients | Replace the x column with the constants for D_x, the y column for D_y | x = D_x/D and y = D_y/D, provided D ≠ 0")

X("m12-chain", 12, M, "Continuity and Differentiability", "Chain rule", "graph",
  "d/dx sin(ax²) = 2ax cos(ax²).",
  params="a:a:-:0.5:0.1:3; x0:x:-:1.2:-3:3",
  out="f0:f(x):-:sin(a*x0**2); d0:f′(x):-:2*a*x0*cos(a*x0**2)", series="f:f(x):-:sin(a*x**2); fp:f′(x):-:2*a*x*cos(a*x**2)", plot="x=-3..3: f, fp",
  eqs="f = sin(a*x**2) | fp = 2*a*x*cos(a*x**2)", scene="graph", tags="chain rule derivative composite function", lab="grapher",
  steps="Write f = sin(u) with u = ax² | df/du = cos u and du/dx = 2ax | Chain rule: df/dx = cos(ax²) × 2ax", ask="d0")

X("m12-continuity", 12, M, "Continuity and Differentiability", "Making a function continuous", "concept",
  "Find k so that the two pieces meet.",
  params="p:Join point x = p:-:2:0.5:5",
  out="k:k for f(x) = kx + 1 (x ≤ p), 3x − 5 (x > p):-:(3*p - 6)/p; fp:f(p):-:3*p - 5",
  series="y:f(x):-:Heaviside(p - x)*((3*p - 6)/p*x + 1) + Heaviside(x - p)*(3*x - 5)", plot="x=-2..8: y", eqs="k*p + 1 = 3*p - 5",
  scene="graph", tags="continuity piecewise function limit left right", ask="k",
  steps="f is continuous at p if the left limit, right limit and f(p) are equal | Left: kp + 1; right: 3p − 5 | Set them equal and solve: k = (3p − 6)/p")

X("m12-rate", 12, M, "Application of Derivatives", "Rate of change: a growing circle", "concept",
  "How fast the area grows when the radius grows steadily.",
  params="r:Radius:cm:5:0.1:50; drdt:Rate of increase of radius:cm/s:0.7:0.01:10",
  out="dAdt:Rate of increase of area:cm^2/s:2*pi*r*drdt; dCdt:Rate of increase of circumference:cm/s:2*pi*drdt", plot="r: dAdt",
  eqs="dAdt = 2*pi*r*drdt", tags="rate of change derivative related rates circle ripple",
  steps="A = πr² | Differentiate with respect to time: dA/dt = 2πr dr/dt | The area grows faster as the circle gets bigger", ask="dAdt")

X("m12-cubic-extrema", 12, M, "Application of Derivatives", "Maxima and minima of a cubic", "graph",
  "Critical points from f′(x) = 0.",
  params="a:a:-:1:0.2:3; b:b:-:-3:-10:10; c:c:-:-9:-20:20; d:d:-:5:-20:20",
  out="x1:Critical point 1:-:(-b + sqrt(b**2 - 3*a*c))/(3*a); x2:Critical point 2:-:(-b - sqrt(b**2 - 3*a*c))/(3*a); fmin:Local minimum value:-:a*((-b + sqrt(b**2 - 3*a*c))/(3*a))**3 + b*((-b + sqrt(b**2 - 3*a*c))/(3*a))**2 + c*(-b + sqrt(b**2 - 3*a*c))/(3*a) + d",
  series="f:f(x):-:a*x**3 + b*x**2 + c*x + d; fp:f′(x):-:3*a*x**2 + 2*b*x + c", plot="x=-5..6: f, fp",
  eqs="f = a*x**3 + b*x**2 + c*x + d | fp = 3*a*x**2 + 2*b*x + c", scene="graph", tags="maxima minima critical points first derivative test cubic",
  steps="Critical points are where f′(x) = 3ax² + 2bx + c = 0 | Solve the quadratic: x = (−b ± √(b² − 3ac))/3a | With a > 0 the larger root is a local minimum, the smaller a local maximum (second derivative test)", ask="x1")

X("m12-box", 12, M, "Application of Derivatives", "Largest open box from a square sheet", "derivation",
  "Cut equal squares from the corners and fold up.",
  params="s:Side of the sheet:cm:18:2:100; x:Side of the cut square:cm:3:0:50",
  out="V:Volume:cm^3:x*(s - 2*x)**2; x_best:Best cut:cm:s/6; V_best:Largest volume:cm^3:2*s**3/27", plot="x: V",
  eqs="V = x*(s - 2*x)**2 | x_best = s/6", tags="maxima minima optimisation open box volume",
  steps="The base is (s − 2x) square and the height is x: V = x(s − 2x)² | dV/dx = (s − 2x)(s − 6x) = 0 | x = s/2 gives no box, so x = s/6 | V″ < 0 there, so it is a maximum: V = 2s³/27", ask="V_best")

X("m12-tangent", 12, M, "Application of Derivatives", "Tangent and normal to a curve", "graph",
  "Tangent line to y = x² at a point.",
  params="a:Point x = a:-:1.5:-4:4",
  out="m:Slope of tangent:-:2*a; c:Tangent y-intercept:-:-a**2; mn:Slope of normal:-:-1/(2*a)",
  series="y:y = x²:-:x**2; tl:Tangent:-:2*a*x - a**2", plot="x=-5..5: y, tl", eqs="m = 2*a | y = 2*a*x - a**2",
  scene="graph", tags="tangent normal slope derivative curve", lab="grapher",
  steps="Slope of the tangent = dy/dx at x = a = 2a | Tangent through (a, a²): y − a² = 2a(x − a), so y = 2ax − a² | The normal is perpendicular: slope −1/2a", ask="m")

X("m12-integral-power", 12, M, "Integrals", "Definite integral of xⁿ", "graph",
  "Area under a power curve.",
  params="n:Power n:-:2:0:5; a:Lower limit a:-:0:0:5; b:Upper limit b:-:3:0.5:6",
  out="I:Integral:-:(b**(n + 1) - a**(n + 1))/(n + 1)", series="y:y = xⁿ:-:x**n", plot="x=0..6: y",
  eqs="I = (b**(n + 1) - a**(n + 1))/(n + 1)", scene="graph", tags="definite integral power rule area fundamental theorem", lab="riemann",
  steps="An antiderivative of xⁿ is xⁿ⁺¹/(n + 1) | The fundamental theorem: ∫ from a to b = F(b) − F(a)", ask="I")

X("m12-riemann", 12, M, "Integrals", "Definite integral as the limit of a sum", "derivation",
  "Rectangles under y = x² close in on b³/3.",
  params="b:Upper limit b:-:3:0.5:6; n:Number of rectangles:-:10:1:200:1",
  out="S:Sum of n left rectangles:-:b**3*(n - 1)*(2*n - 1)/(6*n**2); exact:Exact area b³/3:-:b**3/3; err:Error:-:b**3/3 - b**3*(n - 1)*(2*n - 1)/(6*n**2)",
  plot="n: S", eqs="S = b**3*(n - 1)*(2*n - 1)/(6*n**2) | exact = b**3/3", tags="riemann sum limit of a sum definite integral rectangles", lab="riemann",
  steps="Split [0, b] into n strips of width h = b/n | Left rectangles have heights (kh)² for k = 0 … n − 1 | Sum = h³ Σk² = h³(n − 1)n(2n − 1)/6 | As n → ∞ this tends to b³/3", ask="S")

X("m12-area-parabola", 12, M, "Application of Integrals", "Area under a parabola", "derivation",
  "Area bounded by y² = 4ax and the line x = b.",
  params="a:a:-:1:0.2:5; b:b:-:4:0.5:10",
  out="A:Area:-:8*sqrt(a)*b**1.5/3", series="yu:Upper half:-:2*sqrt(a*x)", plot="x=0..b: yu",
  eqs="A = 8*sqrt(a)*b**(3/2)/3", scene="graph", tags="area under curve parabola application of integrals",
  steps="The upper half is y = 2√(ax) | Area of the upper half = ∫₀ᵇ 2√(ax) dx = (4/3)√a b^(3/2) | By symmetry double it: (8/3)√a b^(3/2)", ask="A")

X("m12-area-ellipse", 12, M, "Application of Integrals", "Area of an ellipse", "derivation",
  "πab by integration.",
  params="a:a:-:5:0.5:10; b:b:-:3:0.5:10",
  out="A:Area:-:pi*a*b", series="yu:Upper half:-:b*sqrt(1 - x**2/a**2)", plot="x=-a..a: yu",
  eqs="A = pi*a*b", scene="graph", tags="area ellipse integration", ask="A",
  steps="The upper half is y = (b/a)√(a² − x²) | ∫₀ᵃ √(a² − x²) dx = πa²/4 (a quarter circle) | So the quarter ellipse has area (b/a)(πa²/4) = πab/4 | Multiply by 4")

X("m12-growth", 12, M, "Differential Equations", "Exponential growth and decay: dy/dx = ky", "derivation",
  "Separating variables gives an exponential.",
  params="y0:y at x = 0:-:100:1:1000; k:k:-:0.3:-2:2; x0:x:-:5:0:20",
  out="y:y(x):-:y0*exp(k*x0); double:Doubling (or halving) time:-:log(2)/Abs(k)", series="yx:y:-:y0*exp(k*x)", plot="x=0..20: yx",
  eqs="y = y0*exp(k*x)", scene="graph", tags="differential equation separable exponential growth decay population", lab="phase",
  steps="dy/dx = ky | Separate: dy/y = k dx | Integrate: ln y = kx + C | Use y(0) = y₀: y = y₀ eᵏˣ", ask="y")

X("m12-linear-de", 12, M, "Differential Equations", "Linear first order equation", "derivation",
  "dy/dx + Py = Q with constant P and Q.",
  params="P:P:-:0.5:0.05:3; Q:Q:-:4:-10:10; y0:y(0):-:0:-20:20; x0:x:-:3:0:20",
  out="y:y(x):-:Q/P + (y0 - Q/P)*exp(-P*x0); yinf:Steady value Q/P:-:Q/P", series="yx:y:-:Q/P + (y0 - Q/P)*exp(-P*x)", plot="x=0..20: yx",
  eqs="y = Q/P + (y0 - Q/P)*exp(-P*x)", scene="graph", tags="linear differential equation integrating factor",
  steps="The integrating factor is e^(∫P dx) = e^(Px) | d/dx (y e^(Px)) = Q e^(Px) | Integrate: y e^(Px) = (Q/P)e^(Px) + C | Use y(0) = y₀ to find C", ask="y")

X("m12-dot", 12, M, "Vector Algebra", "Scalar product and projection", "concept",
  "a · b = |a||b| cos θ.",
  params="A:|a|:-:5:0.1:20; B:|b|:-:3:0.1:20; th:Angle between them:deg:60:0:180",
  out="dot:a · b:-:A*B*cos(th*pi/180); proj:Projection of a on b:-:A*cos(th*pi/180); R:|a + b|:-:sqrt(A**2 + B**2 + 2*A*B*cos(th*pi/180))",
  plot="th: dot", eqs="dot = A*B*cos(th) | R = sqrt(A**2 + B**2 + 2*A*B*cos(th))", scene="vector: A=A, B=B, th=th, R=R",
  tags="dot product scalar product projection vectors angle", lab="vectors", ask="dot,R",
  steps="The scalar product is |a||b| cos θ | It is zero when the vectors are perpendicular | The projection of a on b is a · b / |b| = |a| cos θ | |a + b|² = a² + b² + 2a · b")

X("m12-cross", 12, M, "Vector Algebra", "Vector product and area", "concept",
  "|a × b| = |a||b| sin θ is the area of the parallelogram.",
  params="A:|a|:-:4:0.1:20; B:|b|:-:6:0.1:20; th:Angle between them:deg:30:0:180",
  out="cross:|a × b|:-:A*B*sin(th*pi/180); tri:Area of triangle:-:A*B*sin(th*pi/180)/2", plot="th: cross",
  eqs="cross = A*B*sin(th)", scene="vector: A=A, B=B, th=th", tags="cross product vector product area parallelogram", lab="vectors", ask="cross",
  steps="The vector product has size |a||b| sin θ, perpendicular to both | The parallelogram on a and b has base |a| and height |b| sin θ | So its area is |a × b|, and the triangle is half")

X("m12-line-angle", 12, M, "Three Dimensional Geometry", "Angle between two lines in space", "concept",
  "From direction ratios.",
  params="a1:a₁:-:1:-10:10; b1:b₁:-:2:-10:10; c1:c₁:-:2:-10:10; a2:a₂:-:3:-10:10; b2:b₂:-:-4:-10:10; c2:c₂:-:12:-10:15",
  out="cs:cos θ:-:Abs(a1*a2 + b1*b2 + c1*c2)/(sqrt(a1**2 + b1**2 + c1**2)*sqrt(a2**2 + b2**2 + c2**2)); th:Angle:deg:acos(Abs(a1*a2 + b1*b2 + c1*c2)/(sqrt(a1**2 + b1**2 + c1**2)*sqrt(a2**2 + b2**2 + c2**2)))*180/pi",
  eqs="cs = Abs(a1*a2 + b1*b2 + c1*c2)/(sqrt(a1**2 + b1**2 + c1**2)*sqrt(a2**2 + b2**2 + c2**2))", tags="angle between lines direction ratios 3d",
  steps="Direction ratios give vectors along each line | cos θ = |b₁ · b₂| / (|b₁||b₂|) | Lines are perpendicular when a₁a₂ + b₁b₂ + c₁c₂ = 0", ask="th")

X("m12-plane-distance", 12, M, "Three Dimensional Geometry", "Distance of a point from a plane", "concept",
  "Shortest distance from (x₀, y₀, z₀) to ax + by + cz = d.",
  params="a:a:-:2:-10:10; b:b:-:3:-10:10; c:c:-:-6:-10:10; d:d:-:5:-30:30; x0:x₀:-:1:-10:10; y0:y₀:-:1:-10:10; z0:z₀:-:1:-10:10",
  out="D:Distance:-:Abs(a*x0 + b*y0 + c*z0 - d)/sqrt(a**2 + b**2 + c**2)", eqs="D = Abs(a*x0 + b*y0 + c*z0 - d)/sqrt(a**2 + b**2 + c**2)",
  tags="distance point plane 3d geometry normal", ask="D",
  steps="(a, b, c) is normal to the plane | The distance is the projection of any point-to-plane vector on the unit normal | D = |ax₀ + by₀ + cz₀ − d| / √(a² + b² + c²)")

X("m12-lpp", 12, M, "Linear Programming", "Corner point method", "concept",
  "Maximise Z = px + qy with x + y ≤ A, x ≤ B, x, y ≥ 0.",
  params="p:Profit per unit of x:-:5:0.5:20; q:Profit per unit of y:-:3:0.5:20; A:Limit on x + y:-:10:1:50; B:Limit on x:-:6:1:50",
  out="Z_O:Z at (0, 0):-:0; Z_1:Z at (0, A):-:q*A; Z_2:Z at (min(A, B), A − min(A, B)):-:p*Min(A, B) + q*(A - Min(A, B)); Zmax:Maximum Z:-:Max(q*A, p*Min(A, B) + q*(A - Min(A, B)))",
  eqs="Z = p*x + q*y", tags="linear programming corner point feasible region optimisation", ask="Zmax",
  steps="The feasible region is a polygon bounded by x + y = A, x = B and the axes | A linear Z takes its largest value at a corner | Evaluate Z at each corner and pick the largest")

X("m12-bayes", 12, M, "Probability", "Bayes' theorem: a medical test", "law",
  "How likely is disease after a positive test?",
  params="prior:Prevalence of the disease:-:0.01:0.0001:0.5; sens:Test sensitivity P(+|D):-:0.99:0.5:1; fpr:False positive rate P(+|no D):-:0.05:0.001:0.5",
  out="post:P(disease | positive):-:sens*prior/(sens*prior + fpr*(1 - prior)); pos:P(positive):-:sens*prior + fpr*(1 - prior)", plot="prior: post",
  eqs="post = sens*prior/(sens*prior + fpr*(1 - prior))", tags="bayes theorem conditional probability medical test false positive", ask="post",
  steps="P(D | +) = P(+ | D) P(D) / P(+) | P(+) comes from the total probability theorem: P(+ | D)P(D) + P(+ | not D)P(not D) | With a rare disease most positives are false positives")

X("m12-conditional", 12, M, "Probability", "Conditional probability and independence", "concept",
  "P(A | B) = P(A ∩ B) / P(B).",
  params="PA:P(A):-:0.4:0:1; PB:P(B):-:0.5:0.01:1; PAB:P(A and B):-:0.2:0:1",
  out="PAgB:P(A | B):-:PAB/PB; PBgA:P(B | A):-:PAB/PA; indep:P(A)P(B) (equal to P(A and B) if independent):-:PA*PB",
  eqs="PAgB = PAB/PB", tags="conditional probability independent events multiplication rule", ask="PAgB",
  steps="Given B has happened, only outcomes in B count | P(A | B) = P(A ∩ B)/P(B) | A and B are independent when P(A ∩ B) = P(A)P(B)")

X("m12-binomial-dist", 12, M, "Probability", "Binomial distribution", "concept",
  "Probability of r successes in n trials.", boards=ICSE,
  params="n:Trials:-:10:1:30:1; p:Probability of success:-:0.5:0:1; r:Successes:-:4:0:30:1",
  out="Pr:P(X = r):-:factorial(n)/(factorial(r)*factorial(n - r))*p**r*(1 - p)**(n - r); mean:Mean np:-:n*p; var:Variance npq:-:n*p*(1 - p)",
  plot="r: Pr", eqs="Pr = binomial(n, r)*p**r*(1 - p)**(n - r) | mean = n*p", tags="binomial distribution bernoulli trials probability mean variance", lab="probability", ask="Pr",
  steps="One particular order of r successes and n − r failures has probability pʳqⁿ⁻ʳ | There are nCr such orders | P(X = r) = nCr pʳ qⁿ⁻ʳ | Mean np, variance npq")

# ================================================================ Class 12 laboratory activities
X("m12-mvt", 12, M, "Continuity and Differentiability", "Mean value theorem: f(x) = x³ − x", "graph",
  "Somewhere between a and b the tangent is parallel to the chord.",
  params="a:Left end a:-:0:-3:2; b:Right end b:-:2:-2:3",
  out="slope:Slope of the chord:-:(b**3 - b - a**3 + a)/(b - a); c:The point c:-:sqrt((a**2 + a*b + b**2)/3)",
  eqs="3*c**2 - 1 = (b**3 - b - a**3 + a)/(b - a)", tags="mean value theorem lagrange rolle tangent chord derivative activity",
  steps="f(x) = x³ − x is continuous on [a, b] and differentiable inside | Chord slope = (f(b) − f(a))/(b − a) = a² + ab + b² − 1 | f′(c) = 3c² − 1 | Setting them equal: c = √((a² + ab + b²)/3), which lies between a and b", ask="c")

X("m12-area-between", 12, M, "Application of Integrals", "Area between y = kx and y = x²", "derivation",
  "The region enclosed by a line and a parabola.",
  params="k:Slope of the line:-:1:0.2:4",
  out="xm:Where they meet:-:k; A:Enclosed area:-:k**3/6", plot="k: A", eqs="A = k**3/6",
  tags="area between curves line parabola definite integral activity",
  steps="The curves meet where kx = x², at x = 0 and x = k | Between them the line is above the parabola | A = ∫₀ᵏ (kx − x²) dx = k³/2 − k³/3 | So A = k³/6; for k = 1 this is 1/6", ask="A")

X("m12-by-parts", 12, M, "Integrals", "Integration by parts: ∫ x eˣ dx", "derivation",
  "Choose u = x and dv = eˣ dx.",
  params="b:Upper limit:-:1:0:4",
  out="I:Value of the integral from 0 to b:-:(b - 1)*exp(b) + 1", plot="b: I", eqs="I = (b - 1)*exp(b) + 1",
  tags="integration by parts definite integral exponential ilate activity",
  steps="∫u dv = uv − ∫v du | Take u = x (it gets simpler when differentiated) and dv = eˣ dx, so v = eˣ | ∫x eˣ dx = x eˣ − ∫eˣ dx = (x − 1)eˣ + C | From 0 to b: (b − 1)eᵇ + 1; at b = 1 this is exactly 1", ask="I")

X("m12-skew", 12, M, "Three Dimensional Geometry", "Shortest distance between two skew lines", "concept",
  "Lines x-axis-parallel and y-axis-parallel at different heights.",
  params="h:Height between the lines:-:3:0.5:10; th:Angle between their directions:deg:90:10:90",
  out="d:Shortest distance:-:h; cosang:Cosine of the angle:-:cos(th*pi/180)",
  eqs="d = h", tags="skew lines shortest distance three dimensional geometry vectors activity",
  steps="Skew lines are neither parallel nor meeting | The shortest segment between them is perpendicular to both, along b₁ × b₂ | d = |(a₂ − a₁) · (b₁ × b₂)| / |b₁ × b₂| | For one line in the plane z = 0 and the other in z = h, the common perpendicular is vertical and d = h whatever the angle", ask="d")
