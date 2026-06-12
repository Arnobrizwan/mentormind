"""IGCSE Computer Science (0478) course content.

Original, syllabus-aligned teaching material consumed by seed_demo.
Exports a single COURSE dict (see README.md for the format spec).
"""

LESSON_DATA_REPRESENTATION = """
## Why computers use binary

Every value inside a computer is stored using only two states: on and off,
written as 1 and 0. A single 1 or 0 is a **bit**. Eight bits form a **byte**.
We use binary because electronic components are reliable when they only have
to recognise two voltage levels.

A denary (base 10) number uses column values that are powers of ten. A binary
(base 2) number uses column values that are powers of two:

    128  64  32  16   8   4   2   1

## Worked example 1: binary to denary

Convert `10110101` to denary.

Step 1 - write the column values above each bit:

    128  64  32  16   8   4   2   1
      1   0   1   1   0   1   0   1

Step 2 - add the column values wherever a 1 appears:

    128 + 32 + 16 + 4 + 1 = 181

So `10110101` is **181** in denary. Always check: the largest value an
8-bit number can hold is 255 (all ones), so any answer above 255 must be wrong.

## Hexadecimal

Hexadecimal (base 16) is shorthand for binary. One hex digit represents
exactly four bits, so a byte needs just two hex digits. The digits run
0-9 then A=10, B=11, C=12, D=13, E=14, F=15.

## Worked example 2: denary to hexadecimal

Convert denary `200` to hexadecimal.

Step 1 - divide by 16: 200 / 16 = 12 remainder 8.
Step 2 - the quotient 12 is the first digit. In hex, 12 = C.
Step 3 - the remainder 8 is the second digit.

So 200 = **C8**. Check by converting back: C is 12, so
(12 x 16) + 8 = 192 + 8 = 200. Correct.

## Two's complement: storing negative numbers

To store a negative integer in 8 bits we use **two's complement**. The
left-most bit becomes the **sign bit**: 0 means positive, 1 means negative.

To write -20:

Step 1 - write +20 in binary: `00010100`.
Step 2 - invert every bit (this is the one's complement): `11101011`.
Step 3 - add 1: `11101011 + 1 = 11101100`.

Check the answer: the column values for a two's complement byte are
-128, 64, 32, 16, 8, 4, 2, 1. For `11101100` that is
-128 + 64 + 32 + 8 + 4 = -20. Correct.

## Common exam mistakes

- Forgetting that a single byte only reaches 255, then writing answers
  larger than that for an 8-bit number.
- Adding column values where there is a 0 instead of a 1.
- Treating the two's complement sign bit as a normal +128 column. For a
  signed byte the left-most column is -128, not +128.
- Inverting the bits for two's complement but forgetting the final "add 1".
- Mixing up the direction of conversion when going between hex and binary;
  always group bits into fours starting from the right.
"""

LESSON_TEXT_IMAGE_SOUND = """
## Representing text

Computers store text using a character set, where each character has a unique
binary code. **ASCII** uses 7 bits per character, giving 128 codes - enough
for the English alphabet, digits and punctuation. **Unicode** uses more bits
per character so it can represent the symbols of almost every language plus
emoji, at the cost of larger files.

## Representing images: bitmaps

A bitmap image is a grid of **pixels**. Each pixel stores a colour as a
binary number. The **colour depth** is the number of bits used per pixel.
With a colour depth of n bits, the number of available colours is 2 to the
power n. So 1 bit gives 2 colours, while 8 bits give 256 colours.

The **resolution** is the number of pixels (for example 800 x 600). More
pixels and a greater colour depth give better quality but a larger file.

## Worked example 1: image file size

An image is 100 pixels wide and 50 pixels high with a colour depth of 8 bits.

Step 1 - count the pixels: 100 x 50 = 5000 pixels.
Step 2 - multiply by the colour depth: 5000 x 8 = 40000 bits.
Step 3 - convert to bytes (divide by 8): 40000 / 8 = 5000 bytes.

So the image needs **40000 bits** (5000 bytes), ignoring any header data.

## Representing sound

Sound is analogue, so it must be **sampled** to be stored digitally. At
regular intervals the amplitude of the wave is measured and recorded as a
binary number.

- **Sample rate**: how many samples are taken each second, measured in hertz.
- **Sample resolution (bit depth)**: the number of bits used per sample.

A higher sample rate and resolution give a more accurate recording but a
larger file.

## Worked example 2: sound file size

A sound is sampled at 8000 Hz for 5 seconds using a resolution of 16 bits.

Step 1 - samples taken: 8000 x 5 = 40000 samples.
Step 2 - multiply by the resolution: 40000 x 16 = 640000 bits.

So the file needs **640000 bits** (80000 bytes). The general rule is:
file size = sample rate x duration x bit depth.

## Compression

Compression reduces file size so files transfer faster and use less storage.

- **Lossless** compression lets the original file be reconstructed exactly.
  Run-length encoding, which replaces runs of identical data with a count,
  is one method. It suits text and simple images.
- **Lossy** compression permanently removes data the human eye or ear is
  less likely to notice. It gives smaller files and suits photographs and
  music, but quality is lost and cannot be recovered.

## Common exam mistakes

- Giving file sizes in bytes when the question asks for bits, or vice versa.
  Remember 8 bits = 1 byte.
- Confusing resolution (number of pixels) with colour depth (bits per pixel).
- Saying lossless compression "deletes unimportant data"; that describes
  lossy compression.
- Forgetting to multiply by the duration when calculating a sound file size.
"""

LESSON_HARDWARE_CPU = """
## Hardware and the CPU

**Hardware** is the physical parts of a computer system. The **Central
Processing Unit (CPU)** is the component that processes data and executes the
instructions of a program. Modern CPUs are microprocessors built onto a
single chip.

## Inside the CPU

The CPU contains several key parts:

- **Control Unit (CU)**: manages the flow of data, decodes instructions and
  controls how the other components respond.
- **Arithmetic Logic Unit (ALU)**: performs calculations and logical
  comparisons such as add, subtract and "is equal to".
- **Registers**: tiny, very fast storage locations inside the CPU.
- **Buses**: parallel wires that carry data, addresses and control signals.

The **Program Counter (PC)** is a register that holds the memory address of
the next instruction to fetch.

## The fetch-decode-execute cycle

The CPU repeats a three-stage cycle, sometimes called the machine cycle:

1. **Fetch** - the instruction at the address in the program counter is
   copied from main memory into the CPU. The program counter is then
   increased by one so it points at the next instruction.
2. **Decode** - the control unit works out what the instruction means.
3. **Execute** - the instruction is carried out, often by the ALU.

## Worked example 1: tracing the program counter

Suppose the program counter holds 40 and each instruction is one address
long.

Step 1 - the CPU fetches the instruction stored at address 40.
Step 2 - the program counter is incremented to 41.
Step 3 - the instruction is decoded and executed.
Step 4 - on the next cycle the CPU fetches from address 41.

So after two complete cycles the program counter holds **42**, assuming no
jump instruction changes the flow.

## Factors that affect CPU performance

- **Clock speed** - the number of cycles per second, measured in hertz. A
  higher clock speed means more instructions per second.
- **Number of cores** - each core can run instructions independently, so a
  quad-core CPU can process several instructions at once.
- **Cache size** - cache is fast memory inside or near the CPU. A larger
  cache means the CPU waits less often for data from main memory.

## Worked example 2: comparing clock speeds

A CPU runs at 3 GHz, which is 3 000 000 000 cycles per second. A second CPU
runs at 1.5 GHz.

Step 1 - compare the clock speeds: 3 GHz is twice 1.5 GHz.
Step 2 - if each completes one instruction per cycle, the 3 GHz CPU can
process roughly twice as many instructions per second.

In practice, cache size and number of cores also matter, so clock speed alone
does not decide performance.

## Common exam mistakes

- Saying the ALU decodes instructions; decoding is the job of the control
  unit. The ALU does the arithmetic and logic.
- Forgetting that the program counter is incremented during the fetch stage.
- Confusing storage (the hard drive) with memory (RAM). The CPU fetches
  instructions from RAM, not directly from the hard drive.
- Claiming a higher clock speed always means a faster computer; cores and
  cache also affect real performance.
"""

LESSON_SOFTWARE_OS = """
## Software

**Software** is the set of programs that tell the hardware what to do. It is
divided into two types:

- **System software** - programs that run and manage the computer, such as
  the operating system, device drivers and utilities.
- **Application software** - programs that let the user complete tasks, such
  as a word processor, web browser or spreadsheet.

## The operating system

The **operating system (OS)** is system software that manages the computer's
hardware and provides services for application software. Without it, the user
would have to control the hardware directly.

Key functions of an operating system:

- **Memory management** - decides which programs are loaded into RAM and frees
  memory when programs close.
- **Processor (process) management** - schedules programs so the CPU is
  shared fairly between tasks.
- **Input and output management** - controls peripheral devices such as the
  keyboard, printer and screen, often through device drivers.
- **File management** - organises files and folders on storage, and controls
  access to them.
- **Providing a user interface** - lets the user interact with the computer,
  for example through a graphical user interface.
- **Security** - manages user accounts, passwords and access rights.

## Worked example 1: why multitasking needs an OS

A user is downloading a file, listening to music and typing a document at the
same time.

Step 1 - each task is a separate program needing the CPU and memory.
Step 2 - the OS uses process management to give each program a short slice of
CPU time in turn.
Step 3 - the OS uses memory management to keep each program's data separate
in RAM.

Because the switching happens thousands of times a second, all three tasks
appear to run at once. This is **multitasking**, and the operating system
makes it possible.

## Interrupts

An **interrupt** is a signal sent to the CPU that tells it to pause its
current task and deal with something more urgent, such as a key being pressed
or a printer running out of paper. After handling the interrupt, the CPU
returns to where it left off.

## Worked example 2: handling a print job

Step 1 - the user clicks "print"; the application sends the data to the OS.
Step 2 - the OS passes the data to the printer driver, which translates it
into signals the printer understands.
Step 3 - when the printer is ready it sends an interrupt to the CPU.
Step 4 - the OS responds, sends more data, and the document prints.

The user can keep working because the OS handles the printing in the
background.

## Common exam mistakes

- Listing application software (such as a browser) as system software, or the
  other way round.
- Saying the operating system "is the same as the hardware"; the OS is
  software that controls the hardware.
- Forgetting that device drivers are the link between the OS and a specific
  piece of hardware.
- Describing an interrupt as something the user types in; an interrupt is an
  automatic signal sent to the CPU.
"""

LESSON_NETWORKS_SECURITY = """
## Networks

A **network** is two or more devices connected so they can share data and
resources. A **LAN** (local area network) covers a small area such as a
school. A **WAN** (wide area network) connects devices over a large area; the
internet is the largest WAN.

## Addressing devices

- A **MAC address** identifies the hardware of a network interface card. It
  is set by the manufacturer and does not change.
- An **IP address** identifies a device's location on a network. An IPv4
  address is 32 bits long, written as four numbers such as 192.168.0.5. An
  IPv6 address is 128 bits long to allow far more devices.

The **Domain Name System (DNS)** translates a website name, such as
example.com, into the IP address of the server that hosts it.

## Worked example 1: tracing a web request

Step 1 - the user types a web address into the browser.
Step 2 - the browser asks a DNS server for the matching IP address.
Step 3 - the DNS server returns the IP address of the web server.
Step 4 - the browser sends a request to that IP address and the page is
returned. The MAC address is used to deliver data on the local network, while
the IP address routes it across the internet.

## Network security threats

- **Phishing** - a fake message directs the user to a spoof website to steal
  details such as passwords.
- **Brute-force attack** - software tries many password combinations until one
  works.
- **Denial of service (DoS)** - a server is flooded with requests so it cannot
  respond to genuine users.
- **Malware** - harmful software such as viruses, spyware and keyloggers.
- **Data interception** - data travelling across a network is captured by a
  third party.

## Keeping data safe

- **Firewall** - monitors and filters traffic between a network and external
  networks, blocking anything that breaks its rules.
- **Encryption** - scrambles data so that, even if intercepted, it cannot be
  understood without the key. SSL/TLS encrypts data sent between a browser and
  a web server.
- **Authentication** - confirms who a user is, for example with a password,
  biometrics or two-step verification.

## Worked example 2: symmetric encryption

Step 1 - the sender and receiver agree on the same secret key.
Step 2 - the sender uses the key to scramble (encrypt) the message.
Step 3 - the message travels across the network as unreadable cipher text.
Step 4 - the receiver uses the same key to unscramble (decrypt) it.

Because one key both encrypts and decrypts, this is **symmetric** encryption.
The challenge is sharing the key securely.

## Common exam mistakes

- Saying a firewall encrypts data; a firewall filters traffic, while
  encryption scrambles data.
- Confusing a MAC address (fixed hardware identifier) with an IP address
  (network location).
- Describing phishing as flooding a server; that is a denial of service
  attack.
- Thinking encryption stops data being intercepted; it does not prevent
  interception, it makes the intercepted data unreadable.
"""

LESSON_ALGORITHMS_PSEUDOCODE = """
## Algorithms and pseudocode

An **algorithm** is a step-by-step set of instructions to solve a problem.
**Pseudocode** is a way of writing an algorithm in structured English so it
can be understood before being turned into real program code.

Common pseudocode keywords used at IGCSE include INPUT, OUTPUT, IF...THEN...
ELSE...ENDIF, FOR...NEXT and WHILE...ENDWHILE, with `<-` used for assignment.

## The three basic constructs

- **Sequence** - steps carried out one after another.
- **Selection** - a choice between paths, using IF or CASE.
- **Iteration** - repeating steps, using a FOR loop (count-controlled) or a
  WHILE loop (condition-controlled).

## Worked example 1: finding the largest of ten numbers

    largest <- 0
    FOR count <- 1 TO 10
        INPUT number
        IF number > largest THEN
            largest <- number
        ENDIF
    NEXT count
    OUTPUT largest

Walk-through: the variable `largest` starts at 0. Each time round the loop a
number is input and compared with the current largest. If the new number is
bigger, `largest` is updated. After ten numbers, `largest` holds the biggest
value, which is then output. (If negative inputs were allowed we would set
`largest` from the first input instead of 0.)

## Trace tables

A **trace table** records the value of each variable as an algorithm runs. It
is used to test an algorithm by hand and to find logic errors.

## Worked example 2: tracing a total

Consider this algorithm:

    total <- 0
    FOR n <- 1 TO 4
        total <- total + n
    NEXT n
    OUTPUT total

Trace table:

    n     total
    -     0
    1     1
    2     3
    3     6
    4     10

After the loop `total` is **10**, which the algorithm outputs. The trace
proves the algorithm adds the numbers 1 to 4 correctly.

## Validation and verification

- **Validation** checks that input is sensible, for example a **range check**
  that an age is between 0 and 120, or a **length check** on a password.
- **Verification** checks that data has been entered or copied correctly, for
  example by typing a password twice.

## Worked example 3: a range check

    INPUT age
    WHILE age < 0 OR age > 120
        OUTPUT "Invalid, try again"
        INPUT age
    ENDWHILE

The WHILE loop keeps asking until a valid age is entered, so impossible values
are rejected before the program continues.

## Common exam mistakes

- Forgetting to initialise a variable such as a running total before a loop.
- Using `=` for assignment where pseudocode expects `<-`, or muddling the
  comparison `=` with assignment.
- Starting `largest` at 0 when negative numbers are possible, which would give
  a wrong answer.
- Filling in a trace table with only the final value instead of showing each
  step.
- Confusing validation (is the data sensible?) with verification (was the data
  entered correctly?).
"""


COURSE = {
    "slug": "igcse-computer-science-0478",
    "title": "IGCSE Computer Science (0478)",
    "description": (
        "A study-ready introduction to the Cambridge IGCSE Computer Science "
        "syllabus, covering data representation, hardware and software, "
        "networks, security and algorithm design."
    ),
    "lessons": [
        ("Data Representation: Binary, Hexadecimal and Two's Complement",
         LESSON_DATA_REPRESENTATION),
        ("Text, Images, Sound and Compression", LESSON_TEXT_IMAGE_SOUND),
        ("Hardware and CPU Architecture", LESSON_HARDWARE_CPU),
        ("Software and Operating Systems", LESSON_SOFTWARE_OS),
        ("Networks and Security", LESSON_NETWORKS_SECURITY),
        ("Algorithms and Pseudocode", LESSON_ALGORITHMS_PSEUDOCODE),
    ],
    "quizzes": [
        {
            "title": "Checkpoint: Data Representation",
            "lesson_index": 1,
            "questions": [
                ("Convert the binary number 10110101 to denary.",
                 ["165", "181", "173", "177"], 1, "Number systems"),
                ("Convert the denary number 200 to hexadecimal.",
                 ["C8", "B8", "D8", "CA"], 0, "Number systems"),
                ("Convert the hexadecimal number 2F to denary.",
                 ["47", "31", "79", "45"], 0, "Number systems"),
                ("Using 8-bit two's complement, how is -20 represented?",
                 ["11101100", "11101011", "00010100", "11101101"], 0,
                 "Number systems"),
                ("A sound is sampled at 8000 Hz for 5 seconds with a resolution "
                 "of 16 bits. What is the file size in bits?",
                 ["640000", "320000", "40000", "128000"], 0,
                 "Sound representation"),
                ("Which statement about lossless compression is correct?",
                 ["The original file can be reconstructed exactly.",
                  "Some data is permanently discarded to reduce the size.",
                  "It can only be used on photographs.",
                  "It always reduces a file more than lossy compression."], 0,
                 "Compression"),
            ],
        },
        {
            "title": "Checkpoint: Networks and Security",
            "lesson_index": 4,
            "questions": [
                ("How many bits are in an IPv4 address?",
                 ["32", "48", "64", "128"], 0, "Network addressing"),
                ("What does a MAC address identify?",
                 ["The hardware of a network interface card",
                  "The current location of a device on the internet",
                  "The website a user is visiting",
                  "The amount of data a device can send"], 0,
                 "Network addressing"),
                ("What is the main purpose of a firewall?",
                 ["To monitor and filter traffic between a network and "
                  "external networks",
                  "To permanently encrypt all stored files",
                  "To increase the clock speed of the CPU",
                  "To translate domain names into IP addresses"], 0,
                 "Network security"),
                ("Which of these is an example of a phishing attack?",
                 ["A fake email directing the user to a spoof website to steal "
                  "their details",
                  "Overloading a server with traffic so it cannot respond",
                  "Software that secretly records every key press",
                  "Intercepting data as it travels across a network"], 0,
                 "Cyber threats"),
                ("What does SSL/TLS provide when browsing a website?",
                 ["Encryption of data exchanged between the browser and server",
                  "Faster broadband download speeds",
                  "Automatic backup of the server's hard drive",
                  "Compression of the images on the web page"], 0,
                 "Encryption"),
                ("Which statement describes symmetric encryption?",
                 ["The same key is used to both encrypt and decrypt the data",
                  "A public key encrypts and a different private key decrypts",
                  "No key is required at any stage",
                  "The key changes automatically every second"], 0,
                 "Encryption"),
            ],
        },
    ],
    "short_answers": [
        {
            "prompt": ("Explain how the integer -6 is represented in an 8-bit "
                       "two's complement system. Show each step."),
            "mark_scheme": (
                "- States +6 in binary as 00000110\n"
                "- Inverts all the bits to give 11111001\n"
                "- Adds 1 to give the final answer 11111010\n"
                "- States the most significant bit is the sign bit "
                "(1 indicates a negative number)"
            ),
            "topic": "Number systems",
            "max_score": 4,
        },
        {
            "prompt": ("Describe the stages of the fetch-decode-execute cycle "
                       "carried out by the CPU."),
            "mark_scheme": (
                "- Fetch: the instruction is copied from memory into the CPU "
                "using the address in the program counter\n"
                "- The program counter is then incremented to point at the "
                "next instruction\n"
                "- Decode: the control unit interprets the instruction\n"
                "- Execute: the instruction is carried out, often by the ALU"
            ),
            "topic": "CPU architecture",
            "max_score": 4,
        },
        {
            "prompt": "State and briefly explain three functions of an operating system.",
            "mark_scheme": (
                "- Memory management: allocates and frees RAM for running "
                "programs\n"
                "- Process or processor management: schedules programs so the "
                "CPU is shared\n"
                "- Input/output and file management: controls peripheral "
                "devices and organises storage"
            ),
            "topic": "Operating systems",
            "max_score": 3,
        },
        {
            "prompt": ("Write a pseudocode algorithm that inputs 10 numbers and "
                       "outputs the largest one."),
            "mark_scheme": (
                "- Initialises a variable for the largest value (or sets it "
                "from the first input)\n"
                "- Uses a count-controlled loop that runs 10 times\n"
                "- Compares each input with the current largest and updates it "
                "when the input is greater\n"
                "- Outputs the largest value after the loop ends"
            ),
            "topic": "Algorithms and pseudocode",
            "max_score": 4,
        },
    ],
    "flashcards": [
        ("How many bits are in one byte?", "8 bits.", "Units"),
        ("Convert the hexadecimal digit A to denary.", "10", "Number systems"),
        ("What is the denary value of the binary number 1111?", "15",
         "Number systems"),
        ("Define 'bit'.",
         "The smallest unit of data: a single binary digit, either 0 or 1.",
         "Units"),
        ("What does CPU stand for?", "Central Processing Unit.", "Hardware"),
        ("State the three stages of the machine cycle.",
         "Fetch, decode, execute.", "CPU architecture"),
        ("What does RAM stand for, and is it volatile?",
         "Random Access Memory; it is volatile, so it loses its contents when "
         "the power is switched off.", "Memory"),
        ("Give the formula for the size of a sound file.",
         "File size = sample rate x duration x bit depth.",
         "Sound representation"),
    ],
}
