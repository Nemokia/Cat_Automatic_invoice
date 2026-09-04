# Override Django's default fa locale: enable thousand-separator grouping.
# Without this, NUMBER_GROUPING=0 causes intcomma to produce raw unformatted
# numbers like 1234567 instead of 1,234,567.
NUMBER_GROUPING = 3
THOUSAND_SEPARATOR = ","
DECIMAL_SEPARATOR = "."
