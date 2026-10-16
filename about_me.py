"""Your "About me" content. Edit this file, nothing else.

- Put your photo at  assets/me.jpg  (jpg, jpeg, png or webp; portrait works best).
- Any field you leave as "" (or an empty list) is simply not shown.
- Keep it factual and specific. Short sentences read as confident.
"""

PROFILE = {
    "Name": "Cooper Wherley",
    "Prem Team": "Chelsea",            # shown under your name
    "number": "9",                                     # optional shirt number for the photo card, e.g. "9"
    "position_played": "Center Back, Central Midfielder",                            # optional, e.g. "Central midfielder"

    # The quick facts strip. Remove or add rows freely: (label, value)
    "facts": [
        ("School", "Florida State University"),
        ("Studying", "Computer Science, minor in Mathematics"),
        ("Graduating", "2028"),
        ("Based in", "Tallahassee, FL"),
    ],

    # Two or three short paragraphs. Plain text.
    "bio": [
        "I'm a third year student at Florida State University studying Computer Science with a minor in Mathematics. I like problems where messy real-world data "
        "has to be cleaned, modelled and then explained to someone who has to turn it into understandable insights. I enjoy working with data and building models that can help people make better decisions.",
        "I've played soccer since I was 5. That is where my interest in the numbers behind the game began, "
        "and why this project asks a question every fan has argued about: what is a player really worth?",
    ],

    # Soccer background, newest first: (years, where, what you did)
   

    # Why you built this project (the most important paragraph for a recruiter)
    "why": (
        "From a young age, it was hard for me to comprehend the insane values that some professional EPL players " 
        "were sold for. Now with the knowledge and tools to analyze player performance, I wanted to build something "
        "that could bridge the gap between perceived value and actual performance. EPL's Value Gap compares what the transfer market pays with what a simple, transparent model predicts "
        "from performance, age, position and club. I chose a linear regression on purpose: every number in the "
        "app can be explained, and I tested it on players the model had never seen."
    ),

    # Skills shown as chips
    "skills": ["Python", "pandas", "scikit-learn", "Streamlit", "Altair", "Git", "SQL", "REST APIs"],

    # Links: (label, url). Leave out any you do not want.
    "links": [
        ("GitHub", "https://github.com/Wherleybird"),
        ("LinkedIn", "https://www.linkedin.com/in/cooperwherley"),
        ("Email", "cooperwherleycs@gmail.com"),
    ],
}