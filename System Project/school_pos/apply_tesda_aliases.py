"""Add the official TESDA qualification names as aliases.

The registrar's sheets carry the official titles; the school records its own
wording. With the aliases the import matches them without any hand work.
"""
import django

django.setup()

from tracks.models import Course, Strand

STRAND_ALIASES = {
    "Shielded Metal Arc Welding": [
        "Shielded Metal Arc Welding NC II",
        "Shielded Metal Arc Welding NC I",
        "Shielded Metal Arc Welding (SMAW) NC II",
        "SMAW NC II",
        "SMAW NC I",
        "Welding",
    ],
    "Electronic Product Assembly": [
        "Electronic Products Assembly and Servicing NC II",
        "Electronic Products Assembly and Servicing (NC II)",
        "EPAS NC II",
        "Electronics",
    ],
    "Automotive Servicing": [
        "Automotive Servicing NC II",
        "Automotive Servicing NC I",
        "Automotive Mechanic",
    ],
    "Computer Service System": [
        "Computer Systems Servicing NC II",
        "Computer Systems Servicing (CSS) NC II",
        "Computer Systems Servicing NC I",
        "CSS NC II",
        "ICT Programming",
    ],
    "ICT -(.NET)": [
        "ICT Programming (.NET)",
        "ICT Programming NET",
        ".NET Programming",
    ],
    "ICT - (JAVA)": [
        "ICT Programming (JAVA)",
        "ICT Programming JAVA",
        "Java Programming",
    ],
    "Food and Beverage Servicing": [
        "Food and Beverage Services NC II",
        "Food and Beverage Services (NC II)",
        "Food and Beverage Service NC II",
        "FBS NC II",
        "Food and Beverage Processing NC II",
    ],
    "House Keeping": [
        "Housekeeping NC II",
        "House Keeping NC II",
        "HK NC II",
    ],
    "Bartending": [
        "Bartending NC II",
        "Bartending Services NC II",
        "BTG NC II",
    ],
    "Agricultural Crops Production": [
        "Organic Agriculture Production NC II",
        "Organic Agriculture Production (NC II)",
        "Organic Agriculture NC II",
        "Agricultural Crops Production NC II",
        "Agricultural Crops Production (NC I)",
        "Organic Farming NC II",
    ],
}

COURSE_ALIASES = {
    "Automotive Mechanic": [
        "Automotive Mechanic NC II",
        "Automotive Servicing NC II",
    ],
    "Computer and Electronics": [
        "Computer and Electronics NC II",
        "Computer Systems Servicing NC II",
        "Electronic Products Assembly and Servicing NC II",
    ],
    "Hotel and Restaurant Services": [
        "Hotel and Restaurant Services NC II",
        "Food and Beverage Services NC II",
        "Housekeeping NC II",
        "Tourism Services NC II",
    ],
}


def merge(existing, additions):
    names = [n.strip() for n in (existing or "").split(",") if n.strip()]
    lowered = {n.lower() for n in names}
    for name in additions:
        if name.lower() not in lowered:
            names.append(name)
            lowered.add(name.lower())
    return ", ".join(names)


def main():
    for strand in Strand.objects.all():
        key = next((k for k in STRAND_ALIASES if strand.name.startswith(k)), None)
        if not key:
            continue
        strand.aliases = merge(strand.aliases, STRAND_ALIASES[key])
        strand.save(update_fields=["aliases"])
        print(f"strand  {strand.name[:44]:44} -> {strand.aliases}")

    print()
    for course in Course.objects.all():
        key = next((k for k in COURSE_ALIASES if course.name.startswith(k)), None)
        if not key:
            continue
        course.aliases = merge(course.aliases, COURSE_ALIASES[key])
        course.save(update_fields=["aliases"])
        print(f"course  {course.name[:44]:44} -> {course.aliases}")


if __name__ == "__main__":
    main()
