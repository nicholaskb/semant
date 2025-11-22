import pytest

from agents.core.capability_types import Capability, CapabilityType, CapabilitySet
from agents.core.workflow_models import Workflow, WorkflowStep, WorkflowStatus


def test_capability_equality_and_hash():
    cap1 = Capability(CapabilityType.CODE_REVIEW, "1.0")
    cap2 = Capability(CapabilityType.CODE_REVIEW, "1.0")
    cap3 = Capability(CapabilityType.CODE_REVIEW, "2.0")

    # value equality
    assert cap1 == cap2
    assert cap1 != cap3

    # equality vs enum type
    assert cap1 == CapabilityType.CODE_REVIEW
    assert not (cap1 == CapabilityType.STATIC_ANALYSIS)

    # hash consistency
    s = {cap1}
    assert cap2 in s
    assert cap3 not in s


@pytest.mark.asyncio
async def test_capability_set_membership_and_equality():
    cs = CapabilitySet()
    await cs.initialize()

    cr = Capability(CapabilityType.CODE_REVIEW)
    sa = Capability(CapabilityType.STATIC_ANALYSIS)

    await cs.add(cr)
    await cs.add(sa)

    # Membership by Capability
    assert cr in cs
    # Membership by Enum
    assert CapabilityType.STATIC_ANALYSIS in cs
    # Membership by string value
    assert "code_review" in cs
    assert "static_analysis" in cs
    assert "nonexistent" not in cs

    # Equality to another CapabilitySet with same contents
    other = CapabilitySet({cr, sa})
    await other.initialize()
    assert cs == other

    # Equality to plain set (iterable) of Capability
    assert cs == {cr, sa}


def test_workflow_equality_and_hash():
    w1 = Workflow(id="abc")
    w2 = Workflow(id="abc")
    w3 = Workflow(id="xyz")

    # Equality by id
    assert w1 == w2
    assert w1 != w3

    # Hash compatibility
    d = {w1: "first"}
    assert d[w2] == "first"


