"""IGCSE Mathematics (0580) course content for seed_demo."""

COURSE = {
    "slug": "igcse-mathematics-0580",
    "title": "IGCSE Mathematics (0580)",
    "description": (
        "A complete tour of the core IGCSE Mathematics syllabus: number work, "
        "algebra, graphs, geometry and statistics, with worked examples and "
        "exam-focused practice throughout."
    ),
    "lessons": [
        (
            "Number and Percentages",
            """## Types of number

Before anything else, be fluent with the vocabulary of number. **Integers** are whole numbers (positive, negative or zero). **Prime numbers** have exactly two factors: 1 and themselves (note that 1 is *not* prime). A **multiple** of n is n times an integer; a **factor** of n divides into n exactly. The **highest common factor (HCF)** of two numbers is the largest number that divides both; the **lowest common multiple (LCM)** is the smallest number that both divide into. Writing each number as a product of prime factors makes both easy to find: for 36 = 2² × 3² and 60 = 2² × 3 × 5, the HCF takes the lowest power of each shared prime (2² × 3 = 12) and the LCM takes the highest power of every prime that appears (2² × 3² × 5 = 180).

## Fractions, decimals and percentages

A percentage is simply a fraction with denominator 100, so 35% = 35/100 = 0.35. To find a percentage of an amount, convert to a decimal multiplier: 35% of 80 = 0.35 × 80 = 28. **Percentage change** is always measured against the *original* value:

percentage change = (change ÷ original) × 100

## Worked example 1: percentage change

A bicycle's price rises from $80 to $92. Find the percentage increase.

1. Change = 92 - 80 = 12.
2. Divide by the original: 12 ÷ 80 = 0.15.
3. Multiply by 100: the increase is **15%**.

## Worked example 2: reverse percentage

After a 20% reduction in a sale, a coat costs $44. Find the original price.

1. The sale price is 100% - 20% = 80% of the original, so the multiplier is 0.8.
2. Original price × 0.8 = 44.
3. Original price = 44 ÷ 0.8 = **$55**.

Check: 20% of 55 is 11, and 55 - 11 = 44. Correct.

## Compound interest and growth

When interest is compounded, each year's interest is calculated on the new total, not the starting amount. The formula is:

value = P × (1 + r/100)^n

where P is the principal, r the rate and n the number of years. For example, $2000 invested at 3% per year for 2 years grows to 2000 × 1.03² = 2000 × 1.0609 = **$2121.80**. Notice this is slightly more than two lots of simple interest ($2120) because the second year's interest is earned on a larger amount.

## Standard form

Very large or small numbers are written as A × 10^n where 1 <= A < 10 and n is an integer. So 45 000 = 4.5 × 10^4 and 0.0032 = 3.2 × 10^-3.

## Common exam mistakes

- Dividing a percentage change by the *new* value instead of the original.
- Treating a reverse percentage as a forward one: subtracting 20% of $44 instead of dividing by 0.8.
- Using simple interest (adding the same amount each year) in a compound interest question.
- Writing standard form with A outside the range 1 to 10, e.g. 45 × 10³.
- Confusing HCF with LCM — the HCF can never be bigger than either number; the LCM can never be smaller.
""",
        ),
        (
            "Algebraic Manipulation",
            """## Expanding brackets

To expand a single bracket, multiply every term inside by the term outside: 3(2x - 5) = 6x - 15. To expand a pair of brackets, multiply each term in the first by each term in the second (four products in total):

(x + 3)(x - 5) = x² - 5x + 3x - 15 = x² - 2x - 15

Take particular care with signs: a negative times a negative gives a positive.

## Factorising

Factorising reverses expansion. Always look for a **common factor** first: 6x² + 9x = 3x(2x + 3). For a quadratic x² + bx + c, look for two numbers that multiply to give c and add to give b.

## Worked example 1: factorising a quadratic

Factorise x² - 9x + 20.

1. We need two numbers with product +20 and sum -9.
2. Both numbers must be negative (positive product, negative sum). Try -4 and -5: (-4) × (-5) = 20 and (-4) + (-5) = -9. Yes.
3. So x² - 9x + 20 = **(x - 4)(x - 5)**.

Check by expanding: x² - 5x - 4x + 20 = x² - 9x + 20. Correct.

## Algebraic fractions

Simplify algebraic fractions by factorising top and bottom, then cancelling whole brackets — never cancel individual terms. For example:

(x² - 4)/(x² + 5x + 6) = (x + 2)(x - 2) / ((x + 2)(x + 3)) = (x - 2)/(x + 3)

The bracket (x + 2) cancels because it is a factor of the whole numerator and the whole denominator.

## Laws of indices

When multiplying powers of the same base, add the indices: a^m × a^n = a^(m+n). When dividing, subtract them. When raising a power to a power, multiply: (a^m)^n = a^(mn). Also remember a^0 = 1 and a^-n = 1/a^n. So (a³)² × a⁴ = a^6 × a^4 = a^10.

## Worked example 2: rearranging a formula

Make t the subject of v = u + at.

1. Subtract u from both sides: v - u = at.
2. Divide both sides by a: t = **(v - u)/a**.

The rule is to undo operations in reverse order, doing the same thing to both sides at every step.

## Common exam mistakes

- Sign slips when expanding, e.g. writing (x + 4)(x - 6) = x² + 2x - 24 instead of x² - 2x - 24.
- "Cancelling" single terms in a fraction, e.g. crossing out the x² in (x² + 1)/x². You may only cancel common *factors*.
- Adding indices when you should multiply them: (a³)² is a^6, not a^5.
- Forgetting to multiply *every* term inside a bracket: 3(2x - 5) is 6x - 15, not 6x - 5.
- When rearranging, moving a term across the equals sign without changing its sign.
""",
        ),
        (
            "Equations and Inequalities",
            """## Linear equations

A linear equation has the unknown to the power 1 only. Solve it by collecting the unknowns on one side and the numbers on the other, doing the same operation to both sides at each step.

## Worked example 1: a linear equation with brackets

Solve 3(x - 2) = 2x + 5.

1. Expand the bracket: 3x - 6 = 2x + 5.
2. Subtract 2x from both sides: x - 6 = 5.
3. Add 6 to both sides: **x = 11**.

Check: 3(11 - 2) = 27 and 2(11) + 5 = 27. Correct.

## Simultaneous equations

Two equations with two unknowns can be solved by **elimination** (add or subtract the equations to remove one unknown) or **substitution** (rearrange one equation and substitute into the other).

## Worked example 2: elimination

Solve 2x + y = 7 and x - y = 2.

1. The y terms have opposite signs, so *add* the equations: (2x + x) + (y - y) = 7 + 2, giving 3x = 9.
2. So x = 3.
3. Substitute into x - y = 2: 3 - y = 2, so **y = 1**.

Check in the unused equation: 2(3) + 1 = 7. Correct.

## Quadratic equations

A quadratic equation has the form ax² + bx + c = 0. First try to factorise: x² - 5x + 6 = 0 becomes (x - 2)(x - 3) = 0, so x = 2 or x = 3 — a quadratic usually has two solutions, and you must give both. If it will not factorise, use the quadratic formula:

x = (-b ± √(b² - 4ac)) / (2a)

For 2x² + 3x - 2 = 0: a = 2, b = 3, c = -2, so x = (-3 ± √(9 + 16))/4 = (-3 ± 5)/4, giving x = 1/2 or x = -2.

Before factorising, the equation **must equal zero**. If you are given x² = 5x, rearrange to x² - 5x = 0 and factorise to x(x - 5) = 0, giving x = 0 or x = 5. Dividing both sides by x loses the solution x = 0.

## Inequalities

Inequalities are solved like equations, with one crucial exception: **multiplying or dividing both sides by a negative number reverses the inequality sign**. For example, to solve 5 - 2x > 1: subtract 5 to get -2x > -4, then divide by -2 and flip the sign to get x < 2. Represent solutions on a number line with an open circle for < or > and a filled circle for <= or >=.

## Common exam mistakes

- Forgetting to reverse the inequality when dividing by a negative number.
- Giving only one solution to a quadratic equation.
- Dividing through by the unknown and losing the x = 0 solution.
- In elimination, subtracting equations when the matched terms have opposite signs (you should add), or vice versa.
- Not checking solutions by substituting back — a 10-second check catches most arithmetic slips.
""",
        ),
        (
            "Coordinate Geometry and Graphs",
            """## Gradient and the equation of a line

The **gradient** measures the steepness of a line:

gradient m = (change in y) ÷ (change in x) = (y₂ - y₁)/(x₂ - x₁)

A straight line has equation **y = mx + c**, where m is the gradient and c is the y-intercept (where the line crosses the y-axis). Lines sloping up from left to right have positive gradient; lines sloping down have negative gradient.

## Worked example 1: finding the equation of a line

Find the equation of the line through (1, 3) and (4, 9).

1. Gradient: m = (9 - 3)/(4 - 1) = 6/3 = 2.
2. So far y = 2x + c. Substitute the point (1, 3): 3 = 2(1) + c, so c = 1.
3. The equation is **y = 2x + 1**.

Check with the other point: 2(4) + 1 = 9. Correct.

## Parallel and perpendicular lines

**Parallel** lines have equal gradients: y = 3x + 4 is parallel to y = 3x - 1. **Perpendicular** lines have gradients that multiply to -1, so each gradient is the negative reciprocal of the other: a line perpendicular to y = 3x - 2 has gradient -1/3.

## Midpoint and length of a line segment

The **midpoint** of the segment joining (x₁, y₁) and (x₂, y₂) is the average of the coordinates: ((x₁ + x₂)/2, (y₁ + y₂)/2). The **length** comes from Pythagoras' theorem:

length = √((x₂ - x₁)² + (y₂ - y₁)²)

## Worked example 2: midpoint and length

A is (1, 2) and B is (4, 6). Find the midpoint and the length of AB.

1. Midpoint = ((1 + 4)/2, (2 + 6)/2) = **(2.5, 4)**.
2. Differences: x changes by 3, y changes by 4.
3. Length = √(3² + 4²) = √(9 + 16) = √25 = **5**.

## Curved graphs

A quadratic y = ax² + bx + c gives a **parabola**: a U-shape if a > 0, an upside-down U (a "hill") if a < 0. It is symmetrical about a vertical line through its turning point. The graph of y = k/x is a **reciprocal** curve in two opposite quadrants that never touches the axes. To solve an equation graphically, read off the x-values where two graphs intersect; to find where a graph crosses the x-axis, set y = 0.

## Common exam mistakes

- Inverting the gradient formula and computing change in x over change in y.
- Mixing up the order of subtraction, e.g. (y₂ - y₁)/(x₁ - x₂), which flips the sign.
- Confusing the midpoint (average of coordinates) with half the *difference* of the coordinates.
- Forgetting the square root in the length formula and leaving the answer as 25 instead of 5.
- Saying perpendicular gradients are just negatives of each other; they are negative *reciprocals* (3 and -1/3, not 3 and -3).
""",
        ),
        (
            "Geometry and Mensuration",
            """## Angle facts you must know

Angles on a straight line sum to 180°; angles around a point sum to 360°; vertically opposite angles are equal. With parallel lines, **alternate** angles (Z-shape) are equal, **corresponding** angles (F-shape) are equal, and **co-interior** angles (C-shape) sum to 180°. The angles of a triangle sum to 180° and of any quadrilateral to 360°.

## Polygons

For a polygon with n sides, the interior angles sum to (n - 2) × 180°, and the exterior angles of *any* polygon sum to 360°. In a **regular** polygon all sides and angles are equal, so each exterior angle is 360°/n.

## Worked example 1: a regular octagon

Find the size of one interior angle of a regular octagon (n = 8).

1. Each exterior angle = 360° ÷ 8 = 45°.
2. Interior and exterior angles lie on a straight line, so interior angle = 180° - 45° = **135°**.

Alternatively: sum of interior angles = (8 - 2) × 180° = 1080°, and 1080° ÷ 8 = 135°. Both methods agree.

## Pythagoras' theorem

In a right-angled triangle with hypotenuse c (the side opposite the right angle), a² + b² = c². With legs 5 cm and 12 cm, the hypotenuse is √(25 + 144) = √169 = 13 cm. To find a shorter side, subtract: if the hypotenuse is 10 and one leg is 6, the other leg is √(100 - 36) = 8.

## Perimeter, area and volume

Key formulas (lengths in cm give areas in cm² and volumes in cm³):

- Area of a triangle = ½ × base × perpendicular height
- Area of a trapezium = ½(a + b)h, where a and b are the parallel sides
- Circle: circumference = 2πr, area = πr²
- Prism volume = area of cross-section × length; cylinder volume = πr²h
- Arc length = (θ/360) × 2πr and sector area = (θ/360) × πr² for angle θ

## Worked example 2: cylinder and sector

(a) Find the volume of a cylinder with radius 3 cm and height 10 cm.

1. V = πr²h = π × 3² × 10 = 90π.
2. V ≈ **282.7 cm³** (1 decimal place).

(b) Find the area of a sector of radius 6 cm with angle 60°.

1. The sector is 60/360 = 1/6 of the full circle.
2. Area = (1/6) × π × 6² = 6π ≈ **18.8 cm²**.

## Common exam mistakes

- Using the diameter instead of the radius in πr², which makes the area four times too big.
- Adding the squares when finding a *shorter* side with Pythagoras instead of subtracting.
- Using the slant height of a triangle as the height in ½ × base × height; the height must be perpendicular to the base.
- Quoting area in cm or volume in cm² — always match units to the dimension.
- Rounding too early: keep π in your calculator until the final step, then round.
""",
        ),
        (
            "Probability and Statistics",
            """## The language of probability

Probability measures how likely an event is, on a scale from 0 (impossible) to 1 (certain). For equally likely outcomes:

P(event) = (number of favourable outcomes) ÷ (total number of outcomes)

The probabilities of all possible outcomes of an experiment sum to 1, so P(not A) = 1 - P(A). **Relative frequency** estimates probability from an experiment: if a drawing pin lands point-up 38 times in 50 throws, the estimated probability is 38/50 = 0.76, and the estimate improves with more trials.

## Combined events

For **independent** events (one does not affect the other), multiply: P(A and B) = P(A) × P(B). For **mutually exclusive** events (cannot happen together), add: P(A or B) = P(A) + P(B). A **tree diagram** organises two-stage experiments: multiply along branches, then add the results of different routes to the same outcome.

## Worked example 1: without replacement

A bag holds 3 red and 5 blue counters. Two counters are taken out at random without replacement. Find the probability that both are red.

1. P(first red) = 3/8.
2. One red has gone, leaving 2 red among 7 counters, so P(second red) = 2/7.
3. Multiply along the branch: P(both red) = 3/8 × 2/7 = 6/56 = **3/28**.

The key idea: "without replacement" means the second probability uses a reduced total.

## Averages and spread

- **Mean** = sum of values ÷ number of values
- **Median** = middle value once the data are in order (with an even count, average the middle two)
- **Mode** = the most frequent value
- **Range** = largest value - smallest value (a measure of spread, not an average)

For data in a frequency table, mean = Σfx ÷ Σf: multiply each value x by its frequency f, total those products, and divide by the total frequency.

## Worked example 2: mean from a frequency table

The number of goals scored per match: 0 goals in 4 matches, 1 goal in 7 matches, 2 goals in 6 matches, 3 goals in 3 matches.

1. Σfx = (0 × 4) + (1 × 7) + (2 × 6) + (3 × 3) = 0 + 7 + 12 + 9 = 28.
2. Σf = 4 + 7 + 6 + 3 = 20 matches.
3. Mean = 28 ÷ 20 = **1.4 goals per match**.

Note the mean need not be a whole number even when every data value is.

## Presenting data

A **pie chart** shows proportions: each category's angle is (frequency/total) × 360°. A **scatter diagram** shows the relationship between two variables; describe the correlation as positive, negative or none, and remember correlation does not prove cause.

## Common exam mistakes

- Forgetting to reduce the totals in "without replacement" problems and reusing 3/8 for the second pick.
- Adding probabilities when you should multiply (and vice versa).
- Finding the median without ordering the data first.
- Dividing Σfx by the number of *rows* in the table instead of by Σf.
- Giving a probability greater than 1 or as a ratio like "3:28" — write it as a fraction, decimal or percentage.
""",
        ),
    ],
    "quizzes": [
        {
            "title": "Number and Algebra Check",
            "lesson_index": 1,
            "questions": [
                (
                    "A jacket costing $60 is reduced by 15% in a sale. What is the sale price?",
                    ["$45", "$51", "$9", "$52.50"],
                    1,
                    "Percentages",
                ),
                (
                    "After a 25% increase, a train fare is $80. What was the original fare?",
                    ["$64", "$60", "$100", "$55"],
                    0,
                    "Percentages",
                ),
                (
                    "What is the highest common factor (HCF) of 36 and 60?",
                    ["6", "12", "180", "4"],
                    1,
                    "Number",
                ),
                (
                    "Expand and simplify (x + 4)(x - 6).",
                    ["x² + 2x - 24", "x² - 2x + 24", "x² - 2x - 24", "x² - 10x - 24"],
                    2,
                    "Algebraic manipulation",
                ),
                (
                    "Factorise x² + 7x + 12.",
                    ["(x + 3)(x + 4)", "(x + 2)(x + 6)", "(x + 1)(x + 12)", "(x - 3)(x - 4)"],
                    0,
                    "Algebraic manipulation",
                ),
                (
                    "Simplify (a^3)^2 × a^4.",
                    ["a^9", "a^10", "a^24", "a^11"],
                    1,
                    "Indices",
                ),
            ],
        },
        {
            "title": "Graphs, Geometry and Shape Check",
            "lesson_index": 4,
            "questions": [
                (
                    "What is the gradient of the line through (2, 3) and (6, 11)?",
                    ["2", "1/2", "-2", "8"],
                    0,
                    "Coordinate geometry",
                ),
                (
                    "Which line is parallel to y = 3x - 1?",
                    ["y = -3x + 4", "y = 3x + 4", "y = (1/3)x - 1", "y = -(1/3)x + 2"],
                    1,
                    "Coordinate geometry",
                ),
                (
                    "What is the midpoint of the line segment joining (-2, 5) and (6, -1)?",
                    ["(2, 2)", "(4, -3)", "(4, 2)", "(2, 3)"],
                    0,
                    "Coordinate geometry",
                ),
                (
                    "What is the size of one interior angle of a regular pentagon?",
                    ["72°", "120°", "540°", "108°"],
                    3,
                    "Angles",
                ),
                (
                    "What is the area of a circle of radius 5 cm, to 1 decimal place?",
                    ["31.4 cm²", "78.5 cm²", "314.2 cm²", "15.7 cm²"],
                    1,
                    "Mensuration",
                ),
                (
                    "A right-angled triangle has shorter sides 6 cm and 8 cm. How long is the hypotenuse?",
                    ["10 cm", "14 cm", "5.3 cm", "100 cm"],
                    0,
                    "Pythagoras",
                ),
            ],
        },
    ],
    "short_answers": [
        {
            "prompt": (
                "A laptop is bought for $800 and later sold for $920. "
                "Calculate the percentage profit, showing your method clearly."
            ),
            "mark_scheme": (
                "- Finds the profit: 920 - 800 = $120\n"
                "- Divides the profit by the original price: 120 / 800 = 0.15\n"
                "- States the percentage profit as 15%"
            ),
            "topic": "Percentages",
            "max_score": 3,
        },
        {
            "prompt": (
                "Solve the simultaneous equations 2x + 3y = 12 and x - y = 1. "
                "Show every step of your working."
            ),
            "mark_scheme": (
                "- Rearranges or eliminates correctly, e.g. x = y + 1 substituted to give 2(y + 1) + 3y = 12\n"
                "- Simplifies to 5y = 10 and finds y = 2\n"
                "- Finds x = 3 by substituting back\n"
                "- Checks or presents both values clearly as the solution pair x = 3, y = 2"
            ),
            "topic": "Equations",
            "max_score": 4,
        },
        {
            "prompt": (
                "A cylindrical water tank has radius 4 m and height 9 m. "
                "Calculate its volume, giving your answer to 3 significant figures with correct units."
            ),
            "mark_scheme": (
                "- States or uses the correct formula V = πr²h\n"
                "- Substitutes correctly: V = π × 4² × 9 = 144π\n"
                "- Gives 452 m³ (accept 452.4 m³) with cubic metre units"
            ),
            "topic": "Mensuration",
            "max_score": 3,
        },
        {
            "prompt": (
                "A bag contains 4 red and 6 blue marbles. Two marbles are picked at random "
                "without replacement. Calculate the probability that both marbles are blue."
            ),
            "mark_scheme": (
                "- States P(first blue) = 6/10\n"
                "- States P(second blue) = 5/9, recognising the totals reduce without replacement\n"
                "- Multiplies the probabilities: 6/10 × 5/9 = 30/90\n"
                "- Simplifies to 1/3 (or an equivalent exact form)"
            ),
            "topic": "Probability",
            "max_score": 4,
        },
    ],
    "flashcards": [
        (
            "Gradient of a line through (x₁, y₁) and (x₂, y₂)",
            "m = (y₂ - y₁) / (x₂ - x₁) — change in y divided by change in x.",
            "Coordinate geometry",
        ),
        (
            "The quadratic formula for ax² + bx + c = 0",
            "x = (-b ± √(b² - 4ac)) / (2a)",
            "Equations",
        ),
        (
            "Compound interest multiplier for r% per year over n years",
            "Multiply the principal by (1 + r/100)^n.",
            "Percentages",
        ),
        (
            "Area of a trapezium",
            "½(a + b)h, where a and b are the parallel sides and h the perpendicular distance between them.",
            "Mensuration",
        ),
        (
            "Pythagoras' theorem",
            "In a right-angled triangle, a² + b² = c², where c is the hypotenuse.",
            "Pythagoras",
        ),
        (
            "Sum of the interior angles of an n-sided polygon",
            "(n - 2) × 180°; the exterior angles of any polygon sum to 360°.",
            "Angles",
        ),
        (
            "Probability of two independent events A and B both happening",
            "P(A and B) = P(A) × P(B).",
            "Probability",
        ),
        (
            "Mean of data in a frequency table",
            "Mean = Σfx ÷ Σf — total of (value × frequency) divided by total frequency.",
            "Statistics",
        ),
    ],
}
