"""``engine/reads/consumer_xref.py``: when exact matches settle a lookup (C-D52).

J29 reaches only the generated definition's weights, where a code or name hit (500, 200) is above
the largest contains score (110) and a promoted hit (80) is not. Here the bound and the rules a
contains weight can pre-empt are checked over other weights.
"""

from app.engine.reads.consumer_xref import contains_ceiling, safe_positions
from app.models.schema import ConsumerMatch, ConsumerPromotedMatch


def _promoted(*rules: dict) -> ConsumerPromotedMatch:
    return ConsumerPromotedMatch.model_validate({"projection": "p", "firstMatch": list(rules)})


def test_the_ceiling_is_the_own_contains_weights_together_or_the_highest_promoted_one():
    match = ConsumerMatch.model_validate(
        {
            "own": [
                {"field": "id", "exact": 1000},
                {"field": "code", "exact": 500, "contains": 40},
                {"field": "name", "exact": 200, "contains": 30},
            ],
            "promoted": [
                {
                    "projection": "p",
                    "firstMatch": [
                        {"field": "code", "exact": 80},
                        {"field": "code", "contains": 10},
                    ],
                }
            ],
        }
    )
    assert contains_ceiling(match) == 70
    # A promoted contains weight above the own ones sets the bound.
    heavy = match.model_copy(update={"promoted": (_promoted({"field": "name", "contains": 90}),)})
    assert contains_ceiling(heavy) == 90
    # Without contains weights nothing can pre-empt an exact match.
    assert (
        contains_ceiling(ConsumerMatch.model_validate({"own": [{"field": "id", "exact": 1000}]}))
        == 0
    )


def test_an_exact_rule_after_a_contains_weight_is_not_safe():
    # A related record matching rule 2 exactly may match rule 1's contains first and pass its weight.
    assert safe_positions(
        _promoted(
            {"field": "code", "exact": 80},
            {"field": "name", "exact": 75, "contains": 20},
            {"field": "x", "exact": 70},
        )
    ) == {0, 1}
    # A rule's own contains weight comes after its exact one.
    assert safe_positions(_promoted({"field": "code", "exact": 80, "contains": 10})) == {0}
    assert safe_positions(
        _promoted({"field": "code", "contains": 10}, {"field": "name", "exact": 75})
    ) == {0}
    assert safe_positions(
        _promoted({"field": "code", "exact": 80}, {"field": "name", "exact": 75})
    ) == {0, 1}
