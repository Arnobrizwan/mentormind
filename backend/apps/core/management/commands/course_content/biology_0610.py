"""IGCSE Biology (0610) course content.

Original, syllabus-aligned teaching material consumed by seed_demo.
Exports a single COURSE dict (see README.md for the format spec).
"""

LESSON_CELL_STRUCTURE = """
## Cells: the building blocks of life

A **cell** is the smallest unit of a living organism. All living things are
made of one or more cells. Cells contain **organelles**, each with a specific
job.

## Animal and plant cells

Both animal and plant cells contain:

- **Cell membrane** - controls what enters and leaves the cell.
- **Cytoplasm** - jelly-like fluid where chemical reactions happen.
- **Nucleus** - controls the cell's activities and contains DNA.
- **Mitochondria** - the site of aerobic respiration, releasing energy.
- **Ribosomes** - where proteins are made.

Plant cells have three extra features that animal cells do not:

- **Cell wall** - a tough layer of cellulose that supports the cell.
- **Chloroplasts** - contain chlorophyll and carry out photosynthesis.
- **A large permanent vacuole** - filled with cell sap, keeping the cell firm.

## Specialised cells and organisation

Cells become **specialised** to do particular jobs. A red blood cell has no
nucleus and is packed with haemoglobin to carry oxygen; a root hair cell has a
long extension to absorb water.

Living things are organised in levels of increasing size:

    cell -> tissue -> organ -> organ system -> organism

A **tissue** is a group of similar cells working together, an **organ** is a
group of tissues, and an **organ system** is a group of organs.

## Using a microscope: magnification

A light microscope makes cells appear larger. The magnification is how many
times bigger the image is than the real object:

    magnification = image size / actual size

This can be rearranged to find any value:

    actual size = image size / magnification

## Worked example 1: calculating magnification

A cell is 0.05 mm wide in real life. In a photograph it measures 50 mm wide.
Find the magnification.

Step 1 - make sure both sizes use the same unit. Both are in mm.
Step 2 - apply the formula: magnification = 50 / 0.05 = 1000.

So the magnification is **x1000**. Magnification has no units.

## Worked example 2: calculating actual size

A cell measures 30 mm across a photograph taken at a magnification of x1500.
Find its real width in micrometres.

Step 1 - actual size = image size / magnification = 30 / 1500 = 0.02 mm.
Step 2 - convert mm to micrometres by multiplying by 1000:
0.02 x 1000 = 20 micrometres.

So the cell is **20 micrometres** wide. Remember 1 mm = 1000 micrometres.

## Common exam mistakes

- Mixing up units. The image and actual size must be in the same unit before
  using the formula.
- Writing a unit after a magnification value; magnification is just a number
  with an "x" in front.
- Listing chloroplasts or a cell wall as features of animal cells; only plant
  cells have them.
- Confusing the order of biological organisation; a tissue is smaller than an
  organ, not larger.
- Saying the cell membrane "supports" the cell; that is the job of the plant
  cell wall.
"""

LESSON_MOVEMENT_IN_OUT = """
## Movement in and out of cells

Cells must take in useful substances such as oxygen and glucose and remove
wastes such as carbon dioxide. Three processes move substances across the cell
membrane: diffusion, osmosis and active transport.

## Diffusion

**Diffusion** is the net movement of particles from a region of higher
concentration to a region of lower concentration, down a concentration
gradient. It does not need energy from the cell. Oxygen reaches body cells by
diffusing from the blood, where it is more concentrated, into the cells.

The rate of diffusion increases with:

- a steeper concentration gradient,
- a larger surface area,
- a thinner exchange surface,
- a higher temperature.

## Osmosis

**Osmosis** is the net movement of water molecules from a dilute solution
(high water concentration) to a more concentrated solution (low water
concentration) through a partially permeable membrane. It is really just the
diffusion of water.

## Worked example 1: osmosis in a plant cell

A plant cell is placed in pure water.

Step 1 - the water outside is more dilute than the cell contents.
Step 2 - water moves into the cell by osmosis through the partially permeable
membrane.
Step 3 - the vacuole swells and pushes the cytoplasm against the cell wall.

The cell becomes **turgid** (firm). The strong cell wall stops it bursting, so
turgid cells help support the plant. In a concentrated solution the opposite
happens: water leaves, the cell becomes flaccid and may become **plasmolysed**
as the membrane pulls away from the wall.

## Worked example 2: osmosis in an animal cell

A red blood cell is placed in a concentrated salt solution.

Step 1 - the solution outside is more concentrated than the cell contents.
Step 2 - water leaves the cell by osmosis.
Step 3 - the cell shrinks and crinkles (crenation).

Because an animal cell has no cell wall, it cannot stay turgid; in pure water
it would take in so much water that it bursts.

## Active transport

**Active transport** is the movement of particles against a concentration
gradient, from a lower to a higher concentration, using energy released by
respiration. Root hair cells use active transport to absorb mineral ions from
the soil even though the soil has a lower concentration of ions than the cell.

## Common exam mistakes

- Saying osmosis moves "water and salts"; only water moves in osmosis.
- Forgetting the words "partially permeable membrane" in a definition of
  osmosis.
- Stating that diffusion needs energy from the cell; it does not, but active
  transport does.
- Claiming an animal cell becomes turgid in water; without a cell wall it
  bursts instead.
- Describing movement "down the gradient" as active transport; active
  transport works against the gradient.
"""

LESSON_ENZYMES = """
## Biological molecules

The main groups of nutrients are carbohydrates, proteins and fats (lipids).

- **Carbohydrates** are made of simple sugars; starch and glycogen are large
  carbohydrates used for storage. The test for starch is iodine solution,
  which turns blue-black.
- **Proteins** are made of amino acids joined in chains. The test for protein
  is the Biuret test, which turns from blue to purple.
- **Fats (lipids)** are made of fatty acids and glycerol. The emulsion test
  gives a cloudy white layer.

The test for reducing sugars such as glucose uses Benedict's solution, which
changes from blue to brick-red when heated with the sugar.

## Enzymes

An **enzyme** is a biological catalyst: a protein that speeds up a chemical
reaction without being used up or changed permanently. Enzymes are needed
because reactions in cells would otherwise be far too slow at body
temperature.

Each enzyme has an **active site** with a specific shape. Only a substrate
with a matching shape can fit, which is why enzymes are **specific**. This is
often called the "lock and key" model: the enzyme is the lock and the
substrate is the key.

## Effect of temperature

As temperature rises, particles move faster and collide more often, so the
rate of reaction increases. The rate is fastest at the **optimum temperature**
(about 37 degrees C for human enzymes). Above the optimum the enzyme
**denatures**: the active site changes shape so the substrate no longer fits,
and the reaction slows or stops. Denaturing is permanent.

## Worked example 1: explaining a rate graph

A graph shows reaction rate against temperature, rising to a peak at 40
degrees C then falling sharply to zero by 60 degrees C.

Step 1 - from 0 to 40 degrees C the rate rises because particles gain kinetic
energy and collide more often.
Step 2 - the peak at 40 degrees C is the optimum temperature.
Step 3 - above 40 degrees C the rate falls because the enzyme is denaturing.
Step 4 - by 60 degrees C the active site has changed shape completely, so no
reaction occurs.

## Effect of pH

Each enzyme also has an optimum pH. A pH that is too high or too low changes
the shape of the active site and denatures the enzyme. Stomach protease works
best in acidic conditions, while enzymes in the small intestine prefer
slightly alkaline conditions.

## Worked example 2: a controlled investigation

To test how pH affects an enzyme, you would change the pH (the independent
variable), measure the reaction rate (the dependent variable) and keep
temperature, enzyme concentration and substrate concentration the same (the
control variables). Keeping these constant makes the test fair.

## Common exam mistakes

- Saying an enzyme is "killed" by heat; enzymes are not alive, so the correct
  word is **denatured**.
- Stating that denaturing is reversible; once the active site has changed
  shape it cannot recover.
- Confusing the food tests; iodine is for starch, Benedict's for reducing
  sugars, Biuret for protein.
- Forgetting that very low pH also denatures an enzyme, not just high
  temperature.
"""

LESSON_PLANT_TRANSPORT = """
## Plant nutrition: photosynthesis

**Photosynthesis** is the process by which plants make glucose using carbon
dioxide and water, with light energy absorbed by chlorophyll. The word
equation is:

    carbon dioxide + water -> glucose + oxygen

This happens in the **chloroplasts**, mainly in the leaf. The glucose made is
used for respiration, stored as starch, or used to build other molecules.

A leaf is adapted for photosynthesis: it is broad and flat for a large surface
area, thin so gases diffuse quickly, and full of chloroplasts near the upper
surface where light is strongest.

## Limiting factors

The rate of photosynthesis is controlled by **limiting factors**: light
intensity, carbon dioxide concentration and temperature. Whichever is in
shortest supply limits the rate.

## Worked example 1: reading a limiting-factor graph

A graph shows rate of photosynthesis against light intensity. The line rises
steeply, then levels off.

Step 1 - at low light, increasing the light raises the rate, so light is the
limiting factor.
Step 2 - where the line levels off, adding more light has no effect.
Step 3 - something else, such as carbon dioxide concentration or temperature,
is now the limiting factor.

## Transport in plants: xylem and phloem

Plants have two transport tissues:

- **Xylem** carries water and dissolved mineral ions from the roots up to the
  leaves. It only flows upwards.
- **Phloem** carries dissolved sugars made in the leaves to all parts of the
  plant, a process called translocation. It can flow in both directions.

## Water uptake and transpiration

Water is absorbed from the soil by **root hair cells** by osmosis. The cells
have a large surface area to speed up absorption. Water then passes into the
xylem and travels up to the leaves.

**Transpiration** is the loss of water vapour from the leaves, mainly through
small holes called stomata. As water evaporates from the leaves it pulls more
water up the xylem in a continuous stream, called the transpiration stream.

## Worked example 2: explaining the water pathway

Trace water from soil to air:

Step 1 - water enters a root hair cell by osmosis.
Step 2 - it moves across the root into the xylem.
Step 3 - it travels up the xylem to the leaf.
Step 4 - it evaporates from leaf cells and diffuses out of the stomata as
water vapour.

The rate of transpiration increases in hot, dry, windy and bright conditions
because these speed up evaporation.

## Common exam mistakes

- Swapping xylem and phloem; remember xylem carries water and only goes up,
  while phloem carries sugars in both directions.
- Writing the photosynthesis equation backwards; it is the reverse of
  respiration.
- Saying roots "suck" water in; water moves into root hairs by osmosis.
- Confusing transpiration (loss of water vapour) with translocation (movement
  of sugars in the phloem).
"""

LESSON_CIRCULATION_RESPIRATION = """
## The circulatory system

The **circulatory system** transports substances around the body in blood,
pumped by the heart. Humans have a **double circulation**: blood passes
through the heart twice for each complete circuit. One loop carries blood to
the lungs and back, the other to the rest of the body and back.

## Blood vessels

- **Arteries** carry blood away from the heart at high pressure. They have
  thick muscular walls.
- **Veins** carry blood back to the heart at low pressure. They have valves to
  stop blood flowing backwards.
- **Capillaries** are tiny vessels with walls one cell thick, where substances
  are exchanged with the tissues.

Most arteries carry oxygenated blood and most veins carry deoxygenated blood.
The important exceptions are the **pulmonary artery**, which carries
deoxygenated blood from the heart to the lungs, and the **pulmonary vein**,
which carries oxygenated blood from the lungs back to the heart.

## Worked example 1: tracing blood through the heart

Step 1 - deoxygenated blood from the body enters the right atrium through the
vena cava.
Step 2 - it passes into the right ventricle and is pumped along the pulmonary
artery to the lungs.
Step 3 - oxygenated blood returns through the pulmonary vein into the left
atrium.
Step 4 - it passes into the left ventricle and is pumped through the aorta to
the body.

The left ventricle has the thickest wall because it must pump blood all the
way around the body.

## Blood

Blood is made of:

- **Red blood cells** - contain haemoglobin, which binds oxygen to form
  oxyhaemoglobin and carries it to the tissues. They have no nucleus.
- **White blood cells** - defend against pathogens.
- **Platelets** - help the blood to clot.
- **Plasma** - the liquid that carries cells, nutrients, carbon dioxide and
  wastes.

## Respiration

**Respiration** is the chemical release of energy from glucose in every living
cell. **Aerobic respiration** uses oxygen:

    glucose + oxygen -> carbon dioxide + water (+ energy)

When oxygen runs short, for example during hard exercise, muscle cells use
**anaerobic respiration**, which releases less energy and produces lactic
acid. In yeast, anaerobic respiration produces ethanol and carbon dioxide
instead (fermentation).

## Worked example 2: gas exchange in an alveolus

Step 1 - air rich in oxygen reaches the alveolus.
Step 2 - oxygen diffuses across the thin, moist alveolar wall into the blood,
down a concentration gradient.
Step 3 - carbon dioxide diffuses the other way, from blood into the alveolus,
and is breathed out.

Alveoli are efficient because they give a large surface area, thin moist walls
and a rich blood supply that maintains the concentration gradient.

## Common exam mistakes

- Saying all arteries carry oxygenated blood; the pulmonary artery does not.
- Stating that anaerobic respiration in humans makes ethanol; that happens in
  yeast. In human muscle it makes lactic acid.
- Forgetting that veins, not arteries, contain valves.
- Saying respiration is "breathing"; breathing moves air, while respiration is
  the chemical release of energy inside cells.
"""

LESSON_INHERITANCE_VARIATION = """
## Chromosomes, genes and DNA

Inside the nucleus of a cell are thread-like **chromosomes** made of **DNA**.
A **gene** is a length of DNA that codes for a particular protein and so
controls a characteristic. Different versions of the same gene are called
**alleles**.

Humans have 23 pairs of chromosomes. One pair determines sex: XX is female and
XY is male.

## Key genetics terms

- **Dominant allele** - shows in the organism even if only one copy is
  present. Written with a capital letter, for example B.
- **Recessive allele** - only shows when two copies are present. Written with a
  lower-case letter, for example b.
- **Genotype** - the alleles an organism has, for example Bb.
- **Phenotype** - the characteristic that is seen, for example brown eyes.
- **Homozygous** - two identical alleles (BB or bb).
- **Heterozygous** - two different alleles (Bb).

## Worked example 1: a monohybrid cross

In a plant, tall (T) is dominant to short (t). Cross two heterozygous tall
plants, Tt x Tt.

Step 1 - each parent can pass on T or t.
Step 2 - draw a Punnett square:

           T        t
       +--------+--------+
    T  |   TT   |   Tt   |
       +--------+--------+
    t  |   Tt   |   tt   |
       +--------+--------+

Step 3 - read off the genotypes: 1 TT : 2 Tt : 1 tt.
Step 4 - work out the phenotypes: TT, Tt and Tt are tall, tt is short.

So the ratio of tall to short offspring is **3 : 1**. This means about 75 per
cent are expected to be tall.

## Worked example 2: predicting the sex of a child

Step 1 - the mother is XX, so all her eggs carry X.
Step 2 - the father is XY, so half his sperm carry X and half carry Y.
Step 3 - an X sperm gives XX (girl); a Y sperm gives XY (boy).

So there is a 50 per cent (1 in 2) chance of each sex at every birth.

## Variation

**Variation** is the differences between individuals of the same species.

- **Continuous variation** has a range of values, such as height or mass, and
  is usually controlled by several genes and the environment.
- **Discontinuous variation** has distinct categories with no in-between, such
  as blood group, and is usually controlled by one or a few genes.

A **mutation** is a random change in the DNA. Mutations are the source of new
alleles and can be increased by ionising radiation and some chemicals.

## Common exam mistakes

- Mixing up genotype (the alleles, such as Bb) and phenotype (what is seen,
  such as brown eyes).
- Forgetting that a recessive characteristic needs two recessive alleles to
  appear.
- Writing the offspring ratio as a number of individuals rather than a ratio;
  3 : 1 is a probability, not a guarantee.
- Saying each child's sex depends on the mother; the sperm (X or Y) from the
  father determines sex.
"""


COURSE = {
    "slug": "igcse-biology-0610",
    "title": "IGCSE Biology (0610)",
    "description": (
        "A study-ready introduction to the Cambridge IGCSE Biology syllabus, "
        "covering cells, transport, enzymes, plant and human physiology, and "
        "inheritance."
    ),
    "lessons": [
        ("Cell Structure and Organisation", LESSON_CELL_STRUCTURE),
        ("Movement In and Out of Cells", LESSON_MOVEMENT_IN_OUT),
        ("Enzymes and Biological Molecules", LESSON_ENZYMES),
        ("Plant Nutrition and Transport", LESSON_PLANT_TRANSPORT),
        ("Human Circulation and Respiration", LESSON_CIRCULATION_RESPIRATION),
        ("Inheritance and Variation", LESSON_INHERITANCE_VARIATION),
    ],
    "quizzes": [
        {
            "title": "Checkpoint: Movement In and Out of Cells",
            "lesson_index": 1,
            "questions": [
                ("Which statement correctly defines diffusion?",
                 ["The net movement of particles from a higher to a lower "
                  "concentration, down a gradient",
                  "The movement of water only, from a low to a high solute "
                  "concentration",
                  "The movement of particles from a lower to a higher "
                  "concentration using energy",
                  "The movement of particles that only happens inside a "
                  "nucleus"], 0, "Diffusion"),
                ("Osmosis is the net movement of which substance, and through "
                 "what?",
                 ["Water molecules, from a dilute to a more concentrated "
                  "solution, through a partially permeable membrane",
                  "Water molecules, from a concentrated to a dilute solution, "
                  "through any membrane",
                  "Solute molecules, from a high to a low concentration",
                  "Water and solutes together, down a pressure gradient"], 0,
                 "Osmosis"),
                ("A plant cell is placed in pure water. What happens to it?",
                 ["It becomes turgid", "It becomes plasmolysed",
                  "It becomes flaccid", "It bursts"], 0, "Osmosis"),
                ("A red blood cell is placed in a concentrated salt solution. "
                 "What happens?",
                 ["It shrinks as water leaves it by osmosis",
                  "It bursts as water enters it",
                  "It becomes turgid, supported by its cell wall",
                  "It stays the same because animal cells cannot lose water"],
                 0, "Osmosis"),
                ("What does active transport require that diffusion does not?",
                 ["Energy released by respiration",
                  "A lower concentration outside the cell",
                  "The absence of a membrane",
                  "Bright light"], 0, "Active transport"),
                ("Which change will increase the rate of diffusion across a "
                 "surface?",
                 ["A larger surface area to volume ratio",
                  "A smaller concentration gradient",
                  "A thicker exchange surface",
                  "A lower temperature"], 0, "Diffusion"),
            ],
        },
        {
            "title": "Checkpoint: Circulation and Respiration",
            "lesson_index": 4,
            "questions": [
                ("Which blood vessel carries oxygenated blood from the heart to "
                 "the body?",
                 ["The aorta", "The vena cava", "The pulmonary artery",
                  "The pulmonary vein"], 0, "Circulatory system"),
                ("What does the pulmonary artery carry, and to where?",
                 ["Deoxygenated blood from the heart to the lungs",
                  "Oxygenated blood from the lungs to the heart",
                  "Oxygenated blood from the heart to the body",
                  "Deoxygenated blood from the body to the heart"], 0,
                 "Circulatory system"),
                ("What are the products of aerobic respiration?",
                 ["Carbon dioxide and water",
                  "Glucose and oxygen",
                  "Lactic acid only",
                  "Ethanol and carbon dioxide"], 0, "Respiration"),
                ("Anaerobic respiration in human muscle produces which "
                 "substance?",
                 ["Lactic acid", "Ethanol and carbon dioxide",
                  "Carbon dioxide and water", "Glucose"], 0, "Respiration"),
                ("Which feature makes an alveolus efficient at gas exchange?",
                 ["A large surface area with thin, moist walls and a rich "
                  "blood supply",
                  "A thick muscular wall to pump the air",
                  "A small surface area to limit water loss",
                  "A waxy, waterproof outer covering"], 0, "Gas exchange"),
                ("Which component of blood transports oxygen around the body?",
                 ["Red blood cells containing haemoglobin",
                  "Plasma only",
                  "White blood cells",
                  "Platelets"], 0, "Blood"),
            ],
        },
    ],
    "short_answers": [
        {
            "prompt": ("Describe three differences between a typical plant cell "
                       "and a typical animal cell."),
            "mark_scheme": (
                "- Plant cells have a cellulose cell wall; animal cells do "
                "not\n"
                "- Plant cells have chloroplasts for photosynthesis; animal "
                "cells do not\n"
                "- Plant cells have one large permanent vacuole; animal cells "
                "have small or no vacuoles"
            ),
            "topic": "Cell structure",
            "max_score": 3,
        },
        {
            "prompt": ("Explain how increasing the temperature affects the rate "
                       "of an enzyme-controlled reaction."),
            "mark_scheme": (
                "- As temperature rises, particles gain kinetic energy so "
                "collisions and rate increase\n"
                "- The rate is highest at the optimum temperature\n"
                "- Above the optimum the enzyme denatures and the active site "
                "changes shape\n"
                "- The substrate no longer fits the active site, so the "
                "reaction slows or stops"
            ),
            "topic": "Enzymes",
            "max_score": 4,
        },
        {
            "prompt": ("A cell measures 40 mm across in a photograph taken at a "
                       "magnification of x2000. Calculate the actual width of "
                       "the cell in micrometres, showing your working."),
            "mark_scheme": (
                "- Uses actual size = image size / magnification\n"
                "- Calculates 40 / 2000 = 0.02 mm\n"
                "- Converts to 20 micrometres by multiplying by 1000"
            ),
            "topic": "Microscopy",
            "max_score": 3,
        },
        {
            "prompt": ("Describe how water travels from the roots to the leaves "
                       "of a plant."),
            "mark_scheme": (
                "- Water is absorbed by root hair cells by osmosis\n"
                "- Water passes into the xylem vessels\n"
                "- Water travels up the xylem to the leaves\n"
                "- Water evaporates from the leaves (transpiration), pulling "
                "the column of water up"
            ),
            "topic": "Plant transport",
            "max_score": 4,
        },
    ],
    "flashcards": [
        ("Give the formula for magnification.",
         "Magnification = image size / actual size.", "Microscopy"),
        ("State the word equation for aerobic respiration.",
         "Glucose + oxygen -> carbon dioxide + water (+ energy).",
         "Respiration"),
        ("State the word equation for photosynthesis.",
         "Carbon dioxide + water -> glucose + oxygen (using light and "
         "chlorophyll).", "Plant nutrition"),
        ("Define osmosis.",
         "The net movement of water molecules from a dilute to a more "
         "concentrated solution through a partially permeable membrane.",
         "Movement in and out of cells"),
        ("Which organelle is the site of photosynthesis?",
         "The chloroplast.", "Cell structure"),
        ("What is the role of haemoglobin?",
         "It binds to oxygen in red blood cells to transport it around the "
         "body.", "Blood"),
        ("Define 'enzyme'.",
         "A biological catalyst (a protein) that speeds up a reaction without "
         "being used up.", "Enzymes"),
        ("Name the products of anaerobic respiration in yeast.",
         "Ethanol and carbon dioxide.", "Respiration"),
    ],
}
