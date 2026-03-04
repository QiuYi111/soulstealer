from internal.domain.letters import LettersSystem, Report, Rescript

def test_rescript_initialization():
    r = Rescript(content="测试朱批", row=10, col=5, timestamp="2026-03-04 12:00:00")
    assert r.content == "测试朱批"
    assert r.row == 10
    
def test_report_rescript_deserialization():
    raw_data = {
        "id": 1,
        "type": "密折",
        "content": "奏前正准备审理妖术案。",
        "timestamp": "2026-03-04 12:00:00",
        "author": "知县",
        "rescripts": [
            {"content": "知道了", "row": 0, "col": 2, "timestamp": "2026-03-04 12:05:00"}
        ]
    }
    report = Report(**raw_data)
    assert len(report.rescripts) == 1
    assert isinstance(report.rescripts[0], Rescript)
    assert report.rescripts[0].content == "知道了"

def test_letters_system_add_report_with_rescripts():
    system = LettersSystem()
    report = system.add_report("密折", "内容", "作者")
    assert report.rescripts == []
    
    # Simulate adding rescripts via editor
    report.rescripts.append(Rescript(content="改一下", row=1, col=1, timestamp="now"))
    assert len(report.rescripts) == 1
