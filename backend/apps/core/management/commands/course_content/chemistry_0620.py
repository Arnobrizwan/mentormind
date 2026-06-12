"""IGCSE Chemistry (0620) course content for seed_demo."""

COURSE = {
    "slug": "igcse-chemistry-0620",
    "title": "IGCSE Chemistry (0620)",
    "description": (
        "Core IGCSE Chemistry from particles and atomic structure through "
        "bonding, the mole, acids and salts, metal reactivity and an "
        "introduction to organic chemistry."
    ),
    "lessons": [
        (
            "Particles, States of Matter and Atomic Structure",
            """## The particulate nature of matter

All matter is made of tiny particles. In a **solid** the particles are packed closely in a regular arrangement and only vibrate about fixed positions, so solids keep their shape. In a **liquid** the particles remain close but can slide past one another, so liquids flow and take the shape of their container. In a **gas** the particles are far apart and move rapidly in all directions, so gases fill their container and are easily compressed.

**Diffusion** is the spreading out of particles from a region of higher concentration to one of lower concentration, caused by their random motion — for example, the smell of perfume crossing a room. Lighter molecules diffuse faster: ammonia (Mr = 17) outruns hydrogen chloride (Mr = 36.5) along a tube, so the white ammonium chloride ring forms nearer the HCl end.

Changes of state — melting, boiling, freezing, condensing — involve energy changes but **no change in the particles themselves**, only in their arrangement and movement.

## Inside the atom

An atom has a tiny central **nucleus** of protons and neutrons, surrounded by electrons in shells.

| Particle | Relative charge | Relative mass |
|---|---|---|
| Proton | +1 | 1 |
| Neutron | 0 | 1 |
| Electron | -1 | about 1/2000 |

The **proton number (atomic number, Z)** is the number of protons and defines the element. The **nucleon number (mass number, A)** is protons + neutrons. Atoms are neutral, so electrons = protons.

## Worked example 1: counting particles

How many protons, neutrons and electrons are in an atom of sodium-23 (Z = 11, A = 23)?

1. Protons = atomic number = **11**.
2. Neutrons = A - Z = 23 - 11 = **12**.
3. The atom is neutral, so electrons = protons = **11**.

## Isotopes

**Isotopes** are atoms of the same element with the same number of protons but **different numbers of neutrons** — for example chlorine-35 and chlorine-37. Isotopes have identical chemical properties because chemistry depends on the electrons, and the electron arrangement is the same.

## Electronic configuration

Electrons fill shells from the inside out: the first shell holds up to 2 electrons, the second up to 8, and (for the first 20 elements) the third up to 8. The number of **outer-shell electrons equals the group number**, and the number of occupied shells equals the period number.

## Worked example 2: electronic configuration

Write the electronic configuration of magnesium (Z = 12) and state its group.

1. 12 electrons to place: first shell takes 2, leaving 10.
2. Second shell takes 8, leaving 2.
3. Configuration: **2,8,2** — two outer electrons, so magnesium is in **Group II**.

## Common exam mistakes

- Saying particles "expand" or "get bigger" on heating — only the spacing and motion change.
- Subtracting the wrong way round and giving neutrons = Z - A.
- Confusing mass number with relative atomic mass (Ar can be a decimal because it averages isotopes).
- Claiming isotopes have different chemical properties.
- Writing configurations that overfill a shell, such as 2,10 for magnesium.
""",
        ),
        (
            "Chemical Bonding and Structure",
            """## Why atoms bond

Atoms react to achieve a full outer shell of electrons — the stable electronic structure of a noble gas. They can do this by transferring electrons (ionic bonding), sharing electrons (covalent bonding) or pooling them (metallic bonding).

## Ionic bonding

Ionic bonding occurs between **metals and non-metals**. The metal atom **loses** its outer electrons to form a positive ion (cation); the non-metal atom **gains** those electrons to form a negative ion (anion). The oppositely charged ions are held together by strong electrostatic attraction in a **giant ionic lattice**.

## Worked example 1: forming sodium chloride

Show how sodium (2,8,1) and chlorine (2,8,7) bond ionically.

1. Sodium loses its single outer electron: Na → Na⁺ (now 2,8).
2. Chlorine gains that electron: Cl + e⁻ → Cl⁻ (now 2,8,8).
3. The Na⁺ and Cl⁻ ions attract each other strongly, building a giant lattice of formula **NaCl**.

Typical ionic properties: high melting points (strong forces throughout the lattice), and electrical conduction **only when molten or in aqueous solution**, because the ions must be free to move. Solid ionic compounds do not conduct.

## Covalent bonding

Covalent bonding occurs between **non-metal atoms**, which share pairs of electrons. Each shared pair is one covalent bond. Examples: H₂ (one shared pair), H₂O (two), CH₄ (four), O₂ (a double bond), N₂ (a triple bond).

## Worked example 2: methane

Explain the bonding in methane, CH₄.

1. Carbon (2,4) needs four more electrons; each hydrogen (1) needs one more.
2. Carbon shares one electron pair with each of four hydrogen atoms — four single covalent bonds.
3. Result: carbon has a full shell of 8 outer electrons and each hydrogen has 2.

**Simple molecular** substances (H₂O, CO₂, CH₄) have strong covalent bonds *within* molecules but weak forces *between* molecules, so they have low melting and boiling points and do not conduct electricity. When they melt, only the weak intermolecular forces break — never the covalent bonds.

## Giant covalent structures

**Diamond**: every carbon bonded to four others in a rigid 3-D network — extremely hard, very high melting point, no conduction. **Graphite**: each carbon bonded to three others in layers; the layers slide (soft, a lubricant) and the spare delocalised electron per atom lets graphite **conduct electricity**. Silicon(IV) oxide has a diamond-like giant structure.

## Metallic bonding

A metal is a lattice of positive ions in a "sea" of **delocalised electrons**. This explains why metals conduct electricity (mobile electrons), conduct heat, and are malleable (layers of ions slide without shattering the structure).

## Common exam mistakes

- Saying ionic compounds conduct when solid — the ions are fixed in the lattice.
- Explaining conduction in molten NaCl by "free electrons"; it is the **ions** that move.
- Saying covalent bonds break when a molecular substance boils — only intermolecular forces break.
- Drawing dot-and-cross diagrams with the wrong number of shared pairs, e.g. three bonds in methane.
- Forgetting graphite is the exception: a non-metal giant covalent structure that conducts.
""",
        ),
        (
            "Stoichiometry and the Mole",
            """## Relative masses

The **relative atomic mass (Ar)** of an element is the average mass of its atoms compared with 1/12 of a carbon-12 atom. The **relative molecular (or formula) mass, Mr**, is the sum of the Ar values in the formula. For CO₂: Mr = 12 + (2 × 16) = 44. For H₂SO₄: Mr = (2 × 1) + 32 + (4 × 16) = 98.

## The mole

A **mole** is the amount of substance containing 6.02 × 10²³ particles (the Avogadro constant). One mole of a substance has a mass equal to its Ar or Mr in grams. The central equation is:

moles n = mass m ÷ molar mass M

Rearrangements: m = n × M and M = m ÷ n. For gases, one mole of any gas occupies **24 dm³ at room temperature and pressure (r.t.p.)**, so gas volume = moles × 24 dm³. For solutions, concentration (mol/dm³) = moles ÷ volume (dm³).

## Worked example 1: moles from mass

How many moles are in 11 g of carbon dioxide?

1. Mr of CO₂ = 12 + 32 = 44.
2. n = m/M = 11 ÷ 44.
3. Answer: **0.25 mol**. At r.t.p. this would occupy 0.25 × 24 = 6 dm³.

## Balancing equations

A balanced equation has the same number of each kind of atom on both sides; you may only change the large numbers in front of formulas, never the small subscripts. Example: methane burning — CH₄ + 2O₂ → CO₂ + 2H₂O.

## Reacting mass calculations

The balanced equation gives the **mole ratio** of reactants and products. Strategy: (1) find moles of the known substance; (2) use the ratio to find moles of the target; (3) convert back to mass (or gas volume).

## Worked example 2: mass of product

What mass of magnesium oxide forms when 4.8 g of magnesium burns completely? (2Mg + O₂ → 2MgO; Ar: Mg = 24, O = 16)

1. Moles of Mg = 4.8 ÷ 24 = 0.2 mol.
2. The ratio Mg : MgO is 2 : 2, i.e. 1 : 1, so moles of MgO = 0.2 mol.
3. Mr of MgO = 24 + 16 = 40, so mass = 0.2 × 40 = **8.0 g**.

Sense check: the product is heavier than the magnesium because oxygen atoms have been added.

## Percentage yield and purity

The theoretical yield is the calculated maximum mass of product. Real reactions give less:

percentage yield = (actual mass ÷ theoretical mass) × 100%

Percentage purity = (mass of pure substance ÷ total mass of sample) × 100%.

## Common exam mistakes

- Multiplying instead of dividing: 11 g of CO₂ is 11/44 mol, not 11 × 44.
- Using Ar where the question needs Mr, e.g. taking oxygen gas as 16 instead of 32 (O₂).
- Ignoring the mole ratio and assuming it is always 1 : 1.
- Balancing equations by changing subscripts (turning H₂O into H₂O₂).
- Quoting gas volumes without conditions — 24 dm³/mol applies at r.t.p. only.
""",
        ),
        (
            "Acids, Bases and Salts",
            """## Acids and alkalis

An **acid** is a substance that produces hydrogen ions, H⁺, in aqueous solution; common lab acids are hydrochloric (HCl), sulfuric (H₂SO₄) and nitric (HNO₃). A **base** is a substance that neutralises an acid (metal oxides and hydroxides); an **alkali** is a base that dissolves in water to give hydroxide ions, OH⁻, such as sodium hydroxide and aqueous ammonia.

The **pH scale** runs from 0 to 14: pH < 7 acidic, pH 7 neutral, pH > 7 alkaline. A strong acid such as dilute hydrochloric acid has a pH of about 1. Indicators: litmus is red in acid and blue in alkali; universal indicator gives the full colour range and an approximate pH; methyl orange and thymolphthalein are used in titrations.

## The characteristic reactions of acids

Learn these four general equations — they generate most salt questions:

- acid + metal → salt + **hydrogen**
- acid + base (metal oxide/hydroxide) → salt + **water**
- acid + carbonate → salt + water + **carbon dioxide**
- acid + alkali → salt + water (**neutralisation**: H⁺ + OH⁻ → H₂O)

The salt's name comes from the acid: hydrochloric acid gives **chlorides**, sulfuric acid gives **sulfates**, nitric acid gives **nitrates**.

## Worked example 1: naming and writing an equation

What salt forms when zinc carbonate reacts with dilute sulfuric acid? Write the balanced equation.

1. Sulfuric acid → a sulfate; the metal is zinc, so the salt is **zinc sulfate**.
2. Carbonate + acid also gives water and carbon dioxide.
3. Equation: ZnCO₃ + H₂SO₄ → ZnSO₄ + H₂O + CO₂.

## Preparing a soluble salt

To make pure copper(II) sulfate crystals from insoluble copper(II) oxide: warm dilute sulfuric acid, add copper(II) oxide **in excess** (until no more dissolves) so all the acid is used up, **filter** off the unreacted oxide, then **evaporate** the solution to the crystallisation point, leave to cool and crystallise, and dry the blue crystals between filter papers. For salts of alkalis (e.g. sodium chloride) use **titration** instead, because both reactants are soluble and no excess can be filtered off.

## Worked example 2: a titration calculation

25.0 cm³ of sodium hydroxide solution is neutralised by exactly 20.0 cm³ of 0.125 mol/dm³ hydrochloric acid. Find the concentration of the alkali. (NaOH + HCl → NaCl + H₂O)

1. Moles of HCl = concentration × volume in dm³ = 0.125 × 0.020 = 0.0025 mol.
2. The ratio is 1 : 1, so moles of NaOH = 0.0025 mol.
3. Concentration of NaOH = 0.0025 ÷ 0.025 = **0.1 mol/dm³**.

## Oxides

Metal oxides are generally **basic**; non-metal oxides (CO₂, SO₂) are generally **acidic**. Amphoteric oxides — aluminium oxide and zinc oxide — react with both acids and alkalis.

## Common exam mistakes

- Calling carbon dioxide the gas made when acids react with *metals* (that gas is hydrogen).
- Forgetting to convert cm³ to dm³ in titration calculations (divide by 1000).
- Saying "filter" to separate a dissolved salt from water — dissolved substances pass through filter paper; you must evaporate/crystallise.
- Heating the salt solution to total dryness, which spoils hydrated crystals such as CuSO₄·5H₂O.
- Mixing up the terms base and alkali — every alkali is a base, but not every base is an alkali.
""",
        ),
        (
            "Metals and the Reactivity Series",
            """## The reactivity series

Metals can be ranked by how vigorously they react. A version to memorise, from most to least reactive:

**potassium > sodium > calcium > magnesium > aluminium > (carbon) > zinc > iron > (hydrogen) > copper > silver > gold**

Carbon and hydrogen are slotted in as reference non-metals: carbon can reduce the oxides of metals below it, and metals above hydrogen react with dilute acids while those below do not.

Evidence for the order: potassium, sodium and calcium react with **cold water** to give the hydroxide and hydrogen; magnesium reacts only slowly with water but quickly with **steam** (giving the oxide and hydrogen); zinc and iron react with steam more slowly; copper, silver and gold do not react with water or dilute acids at all.

## Displacement reactions

A **more reactive metal displaces a less reactive metal** from a solution of its salt. This is the cleanest experimental test of relative reactivity.

## Worked example 1: predicting a displacement

Will anything happen when zinc is added to copper(II) sulfate solution? Write the equation.

1. Zinc is above copper in the reactivity series, so zinc displaces copper.
2. Equation: Zn + CuSO₄ → ZnSO₄ + Cu.
3. Observations: the blue colour of the solution fades (Cu²⁺ ions are removed) and a red-brown deposit of copper forms on the zinc. Adding *silver* to copper(II) sulfate would do nothing — silver is less reactive than copper.

In ionic terms zinc is **oxidised** (Zn → Zn²⁺ + 2e⁻, loss of electrons) and copper ions are **reduced** (Cu²⁺ + 2e⁻ → Cu, gain of electrons). Remember OIL RIG: Oxidation Is Loss, Reduction Is Gain (of electrons).

## Extraction of metals

How a metal is extracted depends on its position in the series. Metals **below carbon** (zinc, iron, copper) are extracted by **reduction of the oxide with carbon**, as in the blast furnace, where coke burns to CO₂, which forms carbon monoxide, and CO reduces iron(III) oxide: Fe₂O₃ + 3CO → 2Fe + 3CO₂. Metals **above carbon** (aluminium, magnesium, sodium) must be extracted by **electrolysis** of the molten compound, which is expensive because of the electrical energy required. Unreactive metals such as gold occur **native** (uncombined).

## Worked example 2: choosing an extraction method

Explain why aluminium is extracted by electrolysis but iron is extracted using carbon.

1. Aluminium is **above carbon** in the reactivity series, so carbon cannot remove the oxygen from aluminium oxide.
2. Electrolysis of molten aluminium oxide (dissolved in cryolite to lower its melting point) deposits aluminium at the cathode.
3. Iron is **below carbon**, so the cheaper method — reduction with carbon (as carbon monoxide) in the blast furnace — works.

## Rusting and its prevention

Rusting of iron requires **both water and oxygen**. Barrier methods (paint, oil, plastic coating) exclude them. **Galvanising** coats iron with zinc, which protects even when scratched: zinc is more reactive, so it corrodes preferentially — **sacrificial protection**. Alloying gives stainless steel.

## Common exam mistakes

- Predicting a displacement the wrong way round (a less reactive metal cannot displace a more reactive one).
- Saying carbon can reduce aluminium oxide.
- Defining oxidation as "gaining oxygen" only and then misreading electron-transfer questions — use electron loss/gain as well.
- Stating that rust needs only oxygen (or only water) — both are required.
- Confusing galvanising (sacrificial zinc) with simple painting (a barrier only).
""",
        ),
        (
            "Introduction to Organic Chemistry",
            """## Organic compounds and homologous series

Organic chemistry is the chemistry of carbon compounds. A **homologous series** is a family of compounds with the same general formula, similar chemical properties, the same functional group, and a trend in physical properties (boiling point rises as the chain lengthens). Each member differs from the next by a CH₂ unit.

The main fuels come from **petroleum (crude oil)**, a mixture of hydrocarbons separated by **fractional distillation**: the column is hot at the bottom and cooler at the top; small molecules with low boiling points (refinery gas, petrol) come off near the top, large ones (fuel oil, bitumen) at the bottom. Smaller molecules are more volatile, more flammable and less viscous.

## Alkanes

**Alkanes** have the general formula **CnH2n+2** and only single C-C bonds: they are **saturated**. The first four are methane (CH₄), ethane (C₂H₆), propane (C₃H₈) and butane (C₄H₁₀). Alkanes are fairly unreactive but burn well:

- Complete combustion: fuel + oxygen → carbon dioxide + water
- Incomplete combustion (limited oxygen) also yields carbon monoxide — a toxic gas — and soot.

## Worked example 1: combustion equation

Write the balanced equation for the complete combustion of methane.

1. Reactants and products: CH₄ + O₂ → CO₂ + H₂O.
2. Balance carbon (already 1 each) and hydrogen: 4 H atoms need 2H₂O.
3. Count oxygen on the right: 2 + 2 = 4 atoms = 2O₂. Final equation: **CH₄ + 2O₂ → CO₂ + 2H₂O**.

## Alkenes

**Alkenes** have the general formula **CnH2n** and contain one C=C double bond: they are **unsaturated**. The first two are ethene (C₂H₄) and propene (C₃H₆). Alkenes are made industrially by **cracking** larger alkanes (heat + catalyst), which also helps match supply to the high demand for petrol-sized molecules.

The lab test to distinguish an alkene from an alkane: shake with **aqueous bromine (bromine water)**. An alkene **decolourises it from orange to colourless** (an addition reaction across the double bond); an alkane gives no change.

## Worked example 2: addition reactions of ethene

Predict the products when ethene reacts with (a) bromine, (b) hydrogen, (c) steam.

1. (a) Ethene + bromine → **dibromoethane** (C₂H₄Br₂); the bromine adds across the C=C bond.
2. (b) Ethene + hydrogen (nickel catalyst, heat) → **ethane**; the alkene is saturated to an alkane.
3. (c) Ethene + steam (phosphoric acid catalyst, heat, pressure) → **ethanol** — the industrial route to alcohol.

## Alcohols

**Alcohols** contain the -OH functional group; ethanol (C₂H₅OH) is the key example. Ethanol is made either by **fermentation** of glucose with yeast at about 30 °C (renewable, slow, impure) or by **hydration of ethene** with steam (fast, pure, but uses a finite resource). Ethanol burns cleanly and is used as a fuel and a solvent.

## Polymers

Many small **monomers** join to form a long-chain **polymer**. In **addition polymerisation**, alkene monomers open their double bonds and link: ethene → poly(ethene). The polymer is the only product.

## Common exam mistakes

- Mixing up the general formulas of alkanes (CnH2n+2) and alkenes (CnH2n).
- Saying bromine water turns "clear" — the correct word is **colourless** (clear just means transparent).
- Forgetting incomplete combustion produces carbon monoxide, and why it is dangerous (binds to haemoglobin).
- Putting the fractional distillation column the wrong way up — it is hottest at the bottom.
- Calling cracking "fractional distillation"; cracking breaks molecules, distillation only separates them.
""",
        ),
    ],
    "quizzes": [
        {
            "title": "Atomic Structure and Bonding Check",
            "lesson_index": 1,
            "questions": [
                (
                    "An atom of aluminium has atomic number 13 and mass number 27. How many neutrons does it have?",
                    ["13", "14", "27", "40"],
                    1,
                    "Atomic structure",
                ),
                (
                    "What is the electronic configuration of magnesium (atomic number 12)?",
                    ["2,8,1", "2,8,2", "2,10", "2,2,8"],
                    1,
                    "Atomic structure",
                ),
                (
                    "Isotopes of an element have the same number of protons but a different number of what?",
                    ["Protons", "Neutrons", "Electrons", "Shells"],
                    1,
                    "Atomic structure",
                ),
                (
                    "How does an ionic bond form?",
                    [
                        "Electrons are shared between two non-metal atoms",
                        "Electrons are transferred from a metal atom to a non-metal atom",
                        "Protons are transferred between atoms",
                        "Atoms pool their electrons into a delocalised sea",
                    ],
                    1,
                    "Bonding",
                ),
                (
                    "Why does molten sodium chloride conduct electricity?",
                    [
                        "Its ions are free to move",
                        "Its electrons are free to move",
                        "Its atoms are free to move",
                        "Its covalent bonds break and carry charge",
                    ],
                    0,
                    "Bonding",
                ),
                (
                    "Which of these substances has a giant covalent structure?",
                    ["Iodine", "Sodium chloride", "Diamond", "Copper"],
                    2,
                    "Bonding",
                ),
            ],
        },
        {
            "title": "Moles, Acids and Reactivity Check",
            "lesson_index": 4,
            "questions": [
                (
                    "What is the relative molecular mass (Mr) of sulfuric acid, H₂SO₄? (Ar: H = 1, S = 32, O = 16)",
                    ["96", "98", "49", "82"],
                    1,
                    "The mole",
                ),
                (
                    "How many moles are there in 8 g of sodium hydroxide, NaOH? (Mr = 40)",
                    ["0.2 mol", "5 mol", "320 mol", "0.5 mol"],
                    0,
                    "The mole",
                ),
                (
                    "What is the approximate pH of dilute hydrochloric acid?",
                    ["7", "1", "13", "9"],
                    1,
                    "Acids, bases and salts",
                ),
                (
                    "Which gas is produced when a dilute acid reacts with a metal such as zinc?",
                    ["Hydrogen", "Water vapour", "Carbon dioxide", "Oxygen"],
                    0,
                    "Acids, bases and salts",
                ),
                (
                    "Which metal will displace copper from copper(II) sulfate solution?",
                    ["Silver", "Gold", "Zinc", "Copper"],
                    2,
                    "Reactivity of metals",
                ),
                (
                    "What volume does 0.25 mol of any gas occupy at room temperature and pressure?",
                    ["24 dm³", "6 dm³", "96 dm³", "0.25 dm³"],
                    1,
                    "The mole",
                ),
            ],
        },
    ],
    "short_answers": [
        {
            "prompt": (
                "A drop of food colouring is placed in a beaker of still water and, after some "
                "time, the whole beaker becomes evenly coloured. Name this process and explain "
                "it using the particle model."
            ),
            "mark_scheme": (
                "- Names the process as diffusion\n"
                "- States that particles move randomly (and collide)\n"
                "- States that particles spread from a region of higher concentration to lower concentration until evenly mixed"
            ),
            "topic": "Particulate nature of matter",
            "max_score": 3,
        },
        {
            "prompt": (
                "Sodium chloride melts at 801 °C, but carbon dioxide is a gas at room "
                "temperature. Explain this difference in terms of the structure and bonding "
                "of the two substances."
            ),
            "mark_scheme": (
                "- States sodium chloride is a giant ionic lattice with strong electrostatic attraction between oppositely charged ions\n"
                "- States that large amounts of energy are needed to break these forces, giving a high melting point\n"
                "- States carbon dioxide is a simple molecular (covalent) substance with weak forces between molecules\n"
                "- States that only the weak intermolecular forces (not the covalent bonds) are overcome on boiling, so little energy is needed"
            ),
            "topic": "Bonding",
            "max_score": 4,
        },
        {
            "prompt": (
                "Magnesium burns in oxygen: 2Mg + O₂ → 2MgO. Calculate the mass of magnesium "
                "oxide formed when 6 g of magnesium burns completely. (Ar: Mg = 24, O = 16) "
                "Show your working."
            ),
            "mark_scheme": (
                "- Calculates moles of Mg = 6 / 24 = 0.25 mol\n"
                "- Uses the 1 : 1 mole ratio of Mg to MgO from the equation\n"
                "- Uses Mr of MgO = 40 to find mass = 0.25 × 40 = 10 g"
            ),
            "topic": "The mole",
            "max_score": 3,
        },
        {
            "prompt": (
                "Describe how to prepare pure, dry crystals of copper(II) sulfate starting from "
                "insoluble copper(II) oxide and dilute sulfuric acid."
            ),
            "mark_scheme": (
                "- Warms the dilute sulfuric acid and adds copper(II) oxide in excess (until no more reacts)\n"
                "- Filters to remove the unreacted copper(II) oxide\n"
                "- Evaporates the solution to the crystallisation point, then leaves it to cool and crystallise\n"
                "- Dries the crystals, e.g. between filter papers (not by strong heating)"
            ),
            "topic": "Acids, bases and salts",
            "max_score": 4,
        },
    ],
    "flashcards": [
        (
            "Relative charges and masses of the proton, neutron and electron",
            "Proton: +1, mass 1. Neutron: 0, mass 1. Electron: -1, mass about 1/2000.",
            "Atomic structure",
        ),
        (
            "Definition of isotopes",
            "Atoms of the same element with the same number of protons but different numbers of neutrons.",
            "Atomic structure",
        ),
        (
            "Ionic vs covalent bonding in one line each",
            "Ionic: electrons transferred from metal to non-metal, ions attract. Covalent: electron pairs shared between non-metal atoms.",
            "Bonding",
        ),
        (
            "The mole equation linking mass and molar mass",
            "moles = mass ÷ molar mass (n = m/M); one mole contains 6.02 × 10²³ particles.",
            "The mole",
        ),
        (
            "Molar gas volume at r.t.p.",
            "One mole of any gas occupies 24 dm³ at room temperature and pressure.",
            "The mole",
        ),
        (
            "The four general reactions of acids",
            "Acid + metal → salt + hydrogen; + base → salt + water; + carbonate → salt + water + CO₂; + alkali → salt + water.",
            "Acids, bases and salts",
        ),
        (
            "Reactivity series from potassium to gold",
            "K > Na > Ca > Mg > Al > (C) > Zn > Fe > (H) > Cu > Ag > Au.",
            "Reactivity of metals",
        ),
        (
            "Lab test for an alkene",
            "Shake with bromine water: an alkene turns it from orange to colourless; an alkane gives no change.",
            "Organic chemistry",
        ),
    ],
}
