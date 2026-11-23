from decimal import Decimal, ROUND_HALF_UP

WW = "WW"
PT = "PT"
QA = "QA"
COMPONENTS = (WW, PT, QA)

DEFAULT_WEIGHTS = {
    "core": {"WW": "25", "PT": "50", "QA": "25"},
    "applied": {"WW": "25", "PT": "45", "QA": "30"},
    "specialized": {"WW": "20", "PT": "60", "QA": "20"},
}

DEPED_TRANSMUTATION_TABLE = [
    ["100.00", "100.00", 100],
    ["98.40", "99.99", 99],
    ["96.80", "98.39", 98],
    ["95.20", "96.79", 97],
    ["93.60", "95.19", 96],
    ["92.00", "93.59", 95],
    ["90.40", "91.99", 94],
    ["88.80", "90.39", 93],
    ["87.20", "88.79", 92],
    ["85.60", "87.19", 91],
    ["84.00", "85.59", 90],
    ["82.40", "83.99", 89],
    ["80.80", "82.39", 88],
    ["79.20", "80.79", 87],
    ["77.60", "79.19", 86],
    ["76.00", "77.59", 85],
    ["74.40", "75.99", 84],
    ["72.80", "74.39", 83],
    ["71.20", "72.79", 82],
    ["69.60", "71.19", 81],
    ["68.00", "69.59", 80],
    ["66.40", "67.99", 79],
    ["64.80", "66.39", 78],
    ["63.20", "64.79", 77],
    ["61.60", "63.19", 76],
    ["60.00", "61.59", 75],
    ["56.40", "59.99", 74],
    ["52.80", "56.39", 73],
    ["49.20", "52.79", 72],
    ["45.60", "49.19", 71],
    ["42.00", "45.59", 70],
    ["38.40", "41.99", 69],
    ["34.80", "38.39", 68],
    ["31.20", "34.79", 67],
    ["27.60", "31.19", 66],
    ["24.00", "27.59", 65],
    ["20.40", "23.99", 64],
    ["16.80", "20.39", 63],
    ["13.20", "16.79", 62],
    ["9.60", "13.19", 61],
    ["6.00", "9.59", 60],
]


def to_decimal(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def percentage_score(raw_sum, hps_sum):
    if not hps_sum or to_decimal(hps_sum) <= 0:
        return None
    return to_decimal(raw_sum) * Decimal(100) / to_decimal(hps_sum)


def weighted_score(ps, weight):
    return ps * to_decimal(weight) / Decimal(100)


def initial_grade(component_sums, weights):
    total = Decimal(0)
    for component, (raw_sum, hps_sum) in component_sums.items():
        ps = percentage_score(raw_sum, hps_sum)
        if ps is None:
            continue
        total += weighted_score(ps, weights.get(component, 0))
    return total


def has_scores(component_sums):
    return any(hps_sum and to_decimal(hps_sum) > 0 for _, hps_sum in component_sums.values())


def transmute(initial, table):
    value = to_decimal(initial)
    lowest = None
    for row in table:
        lo = to_decimal(row[0])
        hi = to_decimal(row[1])
        grade = int(row[2])
        if lowest is None or grade < lowest:
            lowest = grade
        if lo <= value <= hi:
            return grade
    return lowest if lowest is not None else None


def quarterly_grade(component_sums, weights, table):
    if not component_sums or not has_scores(component_sums):
        return None
    return transmute(initial_grade(component_sums, weights), table)


def semester_final(quarter_grades):
    available = [g for g in quarter_grades if g is not None]
    if len(available) < len(quarter_grades) or not quarter_grades:
        return None
    total = sum(to_decimal(g) for g in available)
    return int((total / len(available)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def general_average(semester_finals):
    if not semester_finals or any(f is None for f in semester_finals):
        return None
    total = sum(to_decimal(f) for f in semester_finals)
    return int((total / len(semester_finals)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def component_sums_from_scores(items):
    sums = {component: [Decimal(0), Decimal(0)] for component in COMPONENTS}
    for component, raw_score, hps in items:
        if raw_score is None:
            continue
        if component not in sums:
            continue
        sums[component][0] += to_decimal(raw_score)
        sums[component][1] += to_decimal(hps)
    return {component: (values[0], values[1]) for component, values in sums.items()}
