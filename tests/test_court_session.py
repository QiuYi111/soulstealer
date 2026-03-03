from internal.domain.court import CourtSession, SuspectState

def test_suspect_initial_state():
    state = SuspectState()
    assert state.health == 100
    assert state.pain == 0
    assert state.thirst == 0
    assert state.hunger == 0

def test_apply_torture_jiagun():
    session = CourtSession("德清县令", "阿二")
    session.apply_torture("夹棍", "说，谁指使你的？")
    
    # Check attribute deduction
    assert session.state.pain >= 30
    assert session.state.health <= 90
    
    # Check log
    assert len(session.log) == 2
    assert session.log[0]["role"] == "system"
    assert "夹棍" in session.log[0]["content"]
    assert session.log[1]["role"] == "interrogator"
    assert "谁指使你的" in session.log[1]["content"]

def test_apply_torture_zhangzui():
    session = CourtSession("德清县令", "阿二")
    session.apply_torture("掌嘴", "实话实说！")
    
    assert session.state.pain > 0
    assert session.state.health < 100
    assert "掌嘴" in session.log[0]["content"]
