"""IGCSE Physics (0625) course content for seed_demo."""

COURSE = {
    "slug": "igcse-physics-0625",
    "title": "IGCSE Physics (0625)",
    "description": (
        "Core IGCSE Physics from motion and forces through energy, thermal "
        "physics, waves and electricity, built around the equations and "
        "graph skills that examiners reward."
    ),
    "lessons": [
        (
            "Motion and Motion Graphs",
            """## Speed, velocity and acceleration

**Speed** is the distance travelled per unit time: speed = distance ÷ time, measured in metres per second (m/s). **Velocity** is speed in a stated direction — it is a *vector*, so a car going round a roundabout at a steady 10 m/s has constant speed but changing velocity. **Acceleration** is the rate of change of velocity:

a = (change in velocity) ÷ (time taken) = (v - u)/t

measured in m/s². A negative acceleration (deceleration) means the object is slowing down in the direction of travel.

## Worked example 1: average speed

A cyclist covers 150 m in 12 s. Find the average speed.

1. Write the equation: speed = distance ÷ time.
2. Substitute: speed = 150 ÷ 12.
3. Answer: **12.5 m/s**.

Always quote the unit — an answer of "12.5" alone loses a mark.

## Worked example 2: acceleration

A car accelerates uniformly from rest to 24 m/s in 8 s. Find the acceleration.

1. u = 0 m/s ("from rest"), v = 24 m/s, t = 8 s.
2. a = (v - u)/t = (24 - 0)/8.
3. Answer: **3 m/s²**.

## Distance-time graphs

On a distance-time graph:

- The **gradient is the speed**. A steeper line means a faster object.
- A horizontal line means the object is **stationary** (distance not changing).
- A curve with increasing gradient shows acceleration.

To find a speed from the graph, choose two convenient points on the straight section and divide the change in distance by the change in time.

## Speed-time graphs

On a speed-time graph the roles change, and confusing the two graph types is the single most common error in this topic:

- The **gradient is the acceleration**.
- A horizontal line means **constant speed** (not stationary!).
- The **area under the graph is the distance travelled**.

For example, if a train holds 20 m/s for 60 s, the area under that section is a rectangle: 20 × 60 = 1200 m. For a uniformly accelerating section the area is a triangle: ½ × base × height.

## Free fall and terminal velocity

Near the Earth's surface, an object in free fall accelerates at about 9.8 m/s² (often rounded to 10 m/s² in calculations). A skydiver, however, does not accelerate forever: as speed rises, air resistance grows until it balances the weight. With zero resultant force the acceleration becomes zero and the diver falls at constant **terminal velocity**. Opening the parachute increases air resistance, so the diver decelerates to a new, lower terminal velocity.

## Common exam mistakes

- Reading a horizontal line on a *speed*-time graph as "stationary" — it means constant speed.
- Quoting a speed without units, or mixing units (km with seconds).
- Using total time instead of the time interval for one section of a journey.
- Forgetting that the area under a speed-time graph gives distance, and instead multiplying final speed by total time.
- Saying a falling object "has no forces" at terminal velocity — the forces are balanced, not absent.
""",
        ),
        (
            "Forces and Momentum",
            """## What forces do

A force is a push or a pull, measured in **newtons (N)**. Forces can change an object's speed, direction or shape. The **resultant force** is the single force equivalent to all the forces acting together; for forces along one line, add those in one direction and subtract those in the other. If the resultant force on an object is zero, it stays at rest or keeps moving at constant velocity.

## Newton's second law

The resultant force, mass and acceleration are linked by:

**F = ma** (force in N, mass in kg, acceleration in m/s²)

## Worked example 1: using F = ma

A 1200 kg car accelerates at 2.5 m/s². Find the resultant force needed.

1. F = ma.
2. F = 1200 × 2.5.
3. Answer: **3000 N**.

## Mass and weight

**Mass** is the amount of matter in an object, in kilograms; it is the same everywhere. **Weight** is the gravitational force on the object: W = mg, where g ≈ 10 N/kg on Earth. A 70 kg astronaut weighs about 700 N on Earth but only about 112 N on the Moon (g ≈ 1.6 N/kg), while their mass stays 70 kg.

## Friction and air resistance

Friction acts between surfaces and opposes relative motion, transferring kinetic energy to thermal energy. Air resistance (drag) increases with speed, which is why vehicles need a driving force just to hold a steady speed: the driving force balances the drag.

## Momentum

Momentum is mass times velocity:

**p = mv** (kg m/s)

Momentum is a vector, so direction matters. The **principle of conservation of momentum** says that in a collision or explosion, the total momentum before equals the total momentum after, provided no external force acts.

## Worked example 2: a sticking collision

A 2 kg trolley moving at 6 m/s collides with a stationary 4 kg trolley and they stick together. Find their shared velocity after the collision.

1. Total momentum before = (2 × 6) + (4 × 0) = 12 kg m/s.
2. After the collision the combined mass is 2 + 4 = 6 kg, moving at velocity v, so momentum after = 6v.
3. Conservation: 6v = 12, so v = **2 m/s** in the original direction of the 2 kg trolley.

## Impulse

The change in momentum equals force × time (Ft = Δp). Crumple zones and air bags increase the *time* over which a passenger's momentum changes, which reduces the *force* for the same momentum change — a favourite explain-style exam question.

## Common exam mistakes

- Confusing mass with weight, or quoting weight in kilograms.
- Using F = ma with the wrong force — it must be the *resultant* force, not just the driving force.
- Forgetting the stationary object's momentum is zero but its *mass still counts* after a sticking collision.
- Dropping the direction: momenta in opposite directions must be given opposite signs before adding.
- Writing momentum units as kg/m s or N — the unit is kg m/s (equivalently N s).
""",
        ),
        (
            "Energy, Work and Power",
            """## Energy stores and transfers

Energy is measured in **joules (J)** and is never created or destroyed, only transferred between stores — this is the **principle of conservation of energy**. Useful stores to name in answers: kinetic, gravitational potential, elastic potential, chemical, thermal, nuclear. Transfers happen by mechanical working (forces), electrical working, heating, and radiation (light, sound).

## Kinetic and gravitational potential energy

Two formulas dominate this topic:

- Kinetic energy: **KE = ½mv²**
- Gravitational potential energy: **ΔGPE = mgΔh** (g ≈ 10 N/kg)

Notice the v is *squared*: doubling the speed quadruples the kinetic energy — this is why stopping distances grow so quickly with speed.

## Worked example 1: kinetic and potential energy

(a) Find the kinetic energy of an 800 kg car travelling at 10 m/s.

1. KE = ½mv² = ½ × 800 × 10².
2. KE = ½ × 800 × 100.
3. Answer: **40 000 J** (40 kJ).

(b) A 60 kg gymnast climbs 5 m up a rope. Find the gain in gravitational potential energy.

1. ΔGPE = mgΔh = 60 × 10 × 5.
2. Answer: **3000 J**.

## Work done

**Work** is done when a force moves something in the direction of the force:

W = F × d (joules, with F in newtons and d in metres)

Work done equals energy transferred. Pushing against a wall that does not move does no work in the physics sense, however tiring it feels.

## Power

**Power** is the rate of energy transfer:

P = E/t or P = W/t (watts; 1 W = 1 J/s)

## Worked example 2: work and power

A man pushes a crate with a steady force of 200 N through 30 m in 20 s. Find the work done and his power output.

1. W = F × d = 200 × 30 = **6000 J**.
2. P = W/t = 6000 ÷ 20 = **300 W**.

## Efficiency

No machine transfers all its energy usefully; some is always dissipated, usually as thermal energy.

efficiency = (useful energy output ÷ total energy input) × 100%

A motor that takes in 500 J and delivers 350 J of useful output is (350/500) × 100 = 70% efficient. Efficiency can never exceed 100% — if your answer does, a number is upside down.

## Common exam mistakes

- Forgetting to square the speed in ½mv², or squaring m and v together.
- Using weight where mass is needed (or vice versa) in mgΔh.
- Quoting power in joules or energy in watts — watts are joules *per second*.
- Computing efficiency above 100% by dividing input by output.
- Saying energy is "lost". Say it is dissipated or transferred to the thermal store of the surroundings.
""",
        ),
        (
            "Thermal Physics",
            """## The kinetic particle model

All matter is made of particles in constant motion. In a **solid**, particles vibrate about fixed positions in a regular lattice; in a **liquid**, they are still close together but can slide past one another; in a **gas**, they are far apart and move randomly at high speed. **Temperature** measures the average kinetic energy of the particles: heating a substance makes its particles move (or vibrate) faster.

Gas pressure comes from particles colliding with the container walls. Heating a gas in a sealed rigid container raises the pressure because the particles hit the walls harder and more often. **Brownian motion** — the jittering of smoke particles in air — is evidence for fast-moving, invisible air molecules.

## Thermal expansion

Most materials expand when heated because their particles vibrate through larger distances (the particles themselves do **not** get bigger). Applications and hazards include expansion gaps in bridges and railway tracks, and the liquid expanding up the capillary of a thermometer.

## Specific heat capacity

The **specific heat capacity** c of a substance is the energy needed to raise the temperature of 1 kg of it by 1 °C. The energy equation is:

E = mcΔT

Water has an unusually high value, c = 4200 J/(kg °C), which is why it is used as a coolant and why coastal climates are mild.

## Worked example 1: heating water

How much energy is needed to heat 2 kg of water from 20 °C to 50 °C?

1. ΔT = 50 - 20 = 30 °C.
2. E = mcΔT = 2 × 4200 × 30.
3. Answer: **252 000 J** (252 kJ).

## Changes of state

Melting and boiling happen at fixed temperatures with **no temperature change** while the state changes: the supplied energy goes into breaking intermolecular bonds, not into raising the particles' average kinetic energy. This produces the flat sections on a heating curve. Evaporation, unlike boiling, happens at any temperature, only at the surface, and cools the remaining liquid because the most energetic particles escape.

## Worked example 2: reading a heating curve

A solid is heated steadily and its temperature recorded. The graph rises, is flat at 54 °C for four minutes, then rises again.

1. The flat section means the temperature is constant while energy is still supplied.
2. Therefore the substance is melting, and its **melting point is 54 °C**.
3. During those four minutes the energy goes into breaking the bonds between particles, not raising their kinetic energy.

## Transferring thermal energy

- **Conduction**: vibrations (and, in metals, free electrons) pass energy particle to particle. Metals conduct well because their delocalised electrons carry energy quickly.
- **Convection**: in fluids only — heated fluid expands, becomes less dense and rises, setting up a circulating current.
- **Radiation**: infrared waves needing **no medium**; this is how the Sun's energy reaches Earth. Dull black surfaces are the best absorbers and emitters; shiny silver surfaces the worst.

## Common exam mistakes

- Saying particles "expand" when heated — the spacing or amplitude of vibration increases, not the particle size.
- Using the full temperature instead of the temperature *change* ΔT in E = mcΔT.
- Claiming temperature rises during melting or boiling.
- Saying convection happens in solids, or that radiation needs air.
- Writing that "cold gets in" — only energy flows, from hotter to colder.
""",
        ),
        (
            "Waves and Optics",
            """## Describing waves

Waves transfer **energy without transferring matter**. In a **transverse** wave the oscillations are perpendicular to the direction of travel (light, water ripples); in a **longitudinal** wave they are parallel to it (sound), forming compressions and rarefactions.

Key quantities:

- **Wavelength λ**: distance from one crest to the next (m)
- **Amplitude**: maximum displacement from the rest position (not crest-to-trough!)
- **Frequency f**: waves passing a point per second, in hertz (Hz)
- **Wave equation**: v = fλ

## Worked example 1: the wave equation

A sound wave has frequency 200 Hz and wavelength 1.7 m. Find its speed.

1. v = fλ.
2. v = 200 × 1.7.
3. Answer: **340 m/s** — the typical speed of sound in air.

As a follow-up: an echo from a cliff 510 m away returns after t = (2 × 510)/340 = 3 s. Remember the sound travels there *and back*.

## Reflection and refraction

In reflection, the **angle of incidence equals the angle of reflection**, both measured from the **normal** (the line at 90° to the surface). A plane mirror forms a virtual, upright image the same size as the object and as far behind the mirror as the object is in front.

**Refraction** happens when a wave changes speed crossing a boundary. Light entering glass slows down and bends **towards** the normal; leaving glass it speeds up and bends away. The refractive index is n = sin i / sin r. If light inside glass hits the boundary at more than the **critical angle**, it undergoes **total internal reflection** — the principle behind optical fibres.

## Worked example 2: refractive index

Light strikes a glass block at 45° to the normal and refracts at 28°. Find the refractive index.

1. n = sin i / sin r = sin 45° / sin 28°.
2. n = 0.707 / 0.469.
3. Answer: n ≈ **1.5**.

## Lenses

A converging (convex) lens brings parallel rays to a focus at the **principal focus**; the distance from the lens centre to this point is the **focal length**. An object beyond the focal length forms a **real, inverted** image (camera, eye); an object closer than the focal length forms a **virtual, upright, magnified** image — the magnifying glass.

## The electromagnetic spectrum

In order of increasing frequency (decreasing wavelength): **radio, microwave, infrared, visible, ultraviolet, X-rays, gamma rays**. All travel at 3 × 10^8 m/s in a vacuum. Uses: radio for broadcasting, microwaves for communication and heating, infrared for remote controls and thermal imaging, UV for sterilising, X-rays for imaging bones, gamma for cancer treatment. Higher-frequency radiation carries more energy and is more hazardous.

## Sound

Sound is longitudinal, needs a medium (no sound in a vacuum), and humans hear roughly **20 Hz to 20 000 Hz**. Loudness depends on amplitude; pitch depends on frequency.

## Common exam mistakes

- Measuring angles from the surface instead of from the normal.
- Measuring amplitude from crest to trough instead of from the rest position to a crest.
- Forgetting the factor of 2 in echo problems.
- Mixing the units in v = fλ, e.g. using kHz with metres without converting.
- Putting the EM spectrum in the wrong order — learn it both ways with a mnemonic.
""",
        ),
        (
            "Electricity and Magnetism",
            """## Charge and current

Current is the rate of flow of charge: **I = Q/t**, with charge Q in coulombs (C) and current I in amperes (A). In metals the moving charges are electrons, which drift from the negative terminal to the positive terminal — opposite to the conventional current direction shown on diagrams. Current is measured with an **ammeter in series**; potential difference (p.d.) with a **voltmeter in parallel** across the component.

## Resistance and Ohm's law

Potential difference, current and resistance are linked by:

**V = IR** (volts, amperes, ohms)

## Worked example 1: V = IR and power

A 12 V supply drives a current through a 4 Ω resistor.

1. I = V/R = 12 ÷ 4 = **3 A**.
2. The power dissipated: P = VI = 12 × 3 = **36 W**.

Electrical power can also be written P = I²R, and energy as E = Pt — useful for electricity-cost questions, where energy in kilowatt-hours = power (kW) × time (h).

## Series and parallel circuits

In a **series** circuit: the current is the same at every point; the supply p.d. is shared between components; resistances add (R = R₁ + R₂). In a **parallel** circuit: the p.d. across each branch is the same as the supply; the current splits between branches; the combined resistance is *less* than the smallest branch resistance.

## Worked example 2: combining resistors

A 3 Ω and a 6 Ω resistor are connected (a) in series, (b) in parallel.

1. Series: R = 3 + 6 = **9 Ω**.
2. Parallel: 1/R = 1/3 + 1/6 = 2/6 + 1/6 = 3/6, so R = 6/3 = **2 Ω**.
3. Sense check: 2 Ω is smaller than 3 Ω, the smaller branch — as expected for parallel.

Household circuits are wired in parallel so each appliance receives the full mains voltage and can be switched independently; if one fails, the others keep working.

## Electrical safety

The **fuse** (or circuit breaker) is fitted in the **live** wire and melts if the current exceeds its rating, disconnecting the circuit. The **earth** wire connects the metal casing of an appliance to the ground, so a fault current flows safely to earth and blows the fuse instead of making the casing live. Choose a fuse rating just above the appliance's normal working current.

## Magnetism and electromagnetism

Like magnetic poles repel; unlike poles attract. Field lines run from north to south outside a magnet, and the field is strongest where the lines are closest. A current-carrying wire produces a circular magnetic field around itself; coiling the wire into a **solenoid** with an iron core makes a strong electromagnet that can be switched off — the basis of relays and scrapyard cranes.

A current-carrying wire in a magnetic field experiences a force (the **motor effect**); reversing either the current or the field reverses the force. Conversely, moving a wire through a field *induces* an e.m.f. (**electromagnetic induction**) — the principle of the generator. **Transformers** use induction between two coils on an iron core to change alternating voltages: Vs/Vp = Ns/Np.

## Common exam mistakes

- Connecting (or drawing) the voltmeter in series and the ammeter in parallel.
- Using the parallel formula but forgetting the final reciprocal, leaving R as 1/R.
- Saying current is "used up" around a circuit — it is the same everywhere in a series loop.
- Putting the fuse in the neutral wire, or confusing the jobs of the fuse and the earth wire.
- Assuming transformers work with direct current — induction needs a *changing* field, so a.c. only.
""",
        ),
    ],
    "quizzes": [
        {
            "title": "Motion and Forces Check",
            "lesson_index": 1,
            "questions": [
                (
                    "A runner covers 240 m in 30 s. What is her average speed?",
                    ["8 m/s", "7200 m/s", "0.125 m/s", "270 m/s"],
                    0,
                    "Motion",
                ),
                (
                    "A car speeds up from 5 m/s to 20 m/s in 5 s. What is its acceleration?",
                    ["4 m/s²", "3 m/s²", "15 m/s²", "75 m/s²"],
                    1,
                    "Motion",
                ),
                (
                    "What does the gradient of a distance-time graph represent?",
                    ["Acceleration", "Speed", "Distance", "Force"],
                    1,
                    "Motion",
                ),
                (
                    "What resultant force is needed to give a 1500 kg car an acceleration of 2 m/s²?",
                    ["750 N", "1502 N", "3000 N", "0.0013 N"],
                    2,
                    "Forces",
                ),
                (
                    "What is the weight of a 70 kg person on Earth? (g = 10 N/kg)",
                    ["7 N", "70 N", "700 N", "80 N"],
                    2,
                    "Forces",
                ),
                (
                    "What is the momentum of a 3 kg ball moving at 4 m/s?",
                    ["12 kg m/s", "7 kg m/s", "0.75 kg m/s", "24 kg m/s"],
                    0,
                    "Momentum",
                ),
            ],
        },
        {
            "title": "Thermal, Waves and Electricity Check",
            "lesson_index": 4,
            "time_limit_minutes": 10,
            "questions": [
                (
                    "A wave has frequency 50 Hz and wavelength 6 m. What is its speed?",
                    ["300 m/s", "56 m/s", "8.3 m/s", "0.12 m/s"],
                    0,
                    "Waves",
                ),
                (
                    "How much energy is needed to raise the temperature of 0.5 kg of water by 10 °C? (c = 4200 J/(kg °C))",
                    ["42 000 J", "21 000 J", "2 100 J", "84 000 J"],
                    1,
                    "Thermal physics",
                ),
                (
                    "Which method of thermal energy transfer does NOT need a medium?",
                    ["Conduction", "Convection", "Radiation", "Evaporation"],
                    2,
                    "Thermal physics",
                ),
                (
                    "What happens to a ray of light as it passes from air into glass at an angle to the normal?",
                    [
                        "It bends towards the normal because it slows down",
                        "It bends away from the normal because it slows down",
                        "It bends towards the normal because it speeds up",
                        "It continues without changing direction",
                    ],
                    0,
                    "Waves",
                ),
                (
                    "A p.d. of 6 V is applied across a 2 Ω resistor. What current flows?",
                    ["12 A", "3 A", "0.33 A", "4 A"],
                    1,
                    "Electricity",
                ),
                (
                    "A 3 Ω and a 6 Ω resistor are connected in series. What is their combined resistance?",
                    ["2 Ω", "4.5 Ω", "9 Ω", "18 Ω"],
                    2,
                    "Electricity",
                ),
            ],
        },
    ],
    "short_answers": [
        {
            "prompt": (
                "Explain the difference between speed and velocity, and describe what the "
                "gradient and a horizontal section each represent on a speed-time graph."
            ),
            "mark_scheme": (
                "- States that velocity is speed in a stated direction (velocity is a vector, speed a scalar)\n"
                "- States that the gradient of a speed-time graph is the acceleration\n"
                "- States that a horizontal section means constant speed (not stationary)"
            ),
            "topic": "Motion",
            "max_score": 3,
        },
        {
            "prompt": (
                "A 2 kg trolley moving at 9 m/s collides with a stationary 1 kg trolley and they "
                "stick together. State the principle of conservation of momentum and use it to "
                "find their common velocity after the collision."
            ),
            "mark_scheme": (
                "- States that total momentum before a collision equals total momentum after, when no external force acts\n"
                "- Calculates momentum before: 2 × 9 = 18 kg m/s\n"
                "- Uses combined mass 3 kg: 3v = 18\n"
                "- Finds v = 6 m/s in the original direction"
            ),
            "topic": "Momentum",
            "max_score": 4,
        },
        {
            "prompt": (
                "Calculate the energy required to heat 1.5 kg of water from 18 °C to 38 °C. "
                "The specific heat capacity of water is 4200 J/(kg °C). Show your working."
            ),
            "mark_scheme": (
                "- Uses the correct equation E = mcΔT\n"
                "- Finds the temperature change ΔT = 20 °C\n"
                "- Calculates E = 1.5 × 4200 × 20 = 126 000 J (126 kJ) with correct units"
            ),
            "topic": "Thermal physics",
            "max_score": 3,
        },
        {
            "prompt": (
                "Explain two advantages of connecting household appliances in parallel rather "
                "than in series, and state where a fuse should be fitted and what it does."
            ),
            "mark_scheme": (
                "- States that in parallel each appliance receives the full supply voltage\n"
                "- States that appliances can be switched on and off independently (or one failing does not stop the others)\n"
                "- States the fuse is fitted in the live wire\n"
                "- States the fuse melts and breaks the circuit if the current is too large"
            ),
            "topic": "Electricity",
            "max_score": 4,
        },
    ],
    "flashcards": [
        (
            "Equation linking speed, distance and time",
            "speed = distance ÷ time, in m/s.",
            "Motion",
        ),
        (
            "Newton's second law as an equation",
            "F = ma — resultant force (N) = mass (kg) × acceleration (m/s²).",
            "Forces",
        ),
        (
            "Kinetic energy formula",
            "KE = ½mv² — doubling the speed quadruples the kinetic energy.",
            "Energy",
        ),
        (
            "Gravitational potential energy formula",
            "ΔGPE = mgΔh, with g ≈ 10 N/kg near the Earth's surface.",
            "Energy",
        ),
        (
            "Definition and unit of momentum",
            "Momentum p = mv; a vector measured in kg m/s.",
            "Momentum",
        ),
        (
            "Specific heat capacity of a substance",
            "The energy needed to raise the temperature of 1 kg by 1 °C; E = mcΔT.",
            "Thermal physics",
        ),
        (
            "The wave equation",
            "v = fλ — wave speed (m/s) = frequency (Hz) × wavelength (m).",
            "Waves",
        ),
        (
            "Ohm's law and the unit of resistance",
            "V = IR; resistance is measured in ohms (Ω), where 1 Ω = 1 V/A.",
            "Electricity",
        ),
    ],
}
