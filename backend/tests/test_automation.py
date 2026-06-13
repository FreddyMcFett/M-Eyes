from app.models import AutomationRule, IPAddress, Network
from app.services import automation


def test_kinds_endpoint(client, auth_headers):
    resp = client.get("/api/v1/automation/kinds", headers=auth_headers)
    assert resp.status_code == 200
    assert "asset_reconcile" in resp.json()["kinds"]


def test_rule_crud_and_run(client, db_session, auth_headers):
    net = Network(cidr="10.0.0.0/24")
    db_session.add(net)
    db_session.flush()
    db_session.add(IPAddress(network_id=net.id, ip="10.0.0.7", mac="de:ad:be:ef:00:01"))
    db_session.commit()

    created = client.post("/api/v1/automation", headers=auth_headers, json={
        "name": "nightly-recon", "kind": "asset_reconcile", "interval_seconds": 3600,
    })
    assert created.status_code == 201, created.text
    rule_id = created.json()["id"]

    run = client.post(f"/api/v1/automation/{rule_id}/run", headers=auth_headers)
    assert run.status_code == 200
    assert run.json()["status"] == "ok"

    rule = db_session.get(AutomationRule, rule_id)
    assert rule.run_count == 1
    assert rule.next_run_at is not None


def test_invalid_kind_rejected(client, auth_headers):
    resp = client.post("/api/v1/automation", headers=auth_headers,
                       json={"name": "bad", "kind": "does_not_exist"})
    assert resp.status_code == 422


def test_run_due_executes_enabled_rules(db_session):
    db_session.add(AutomationRule(name="recon", kind="asset_reconcile", enabled=True,
                                  interval_seconds=60, next_run_at=None))
    db_session.commit()
    ran = automation.run_due(db_session)
    assert ran == 1


def test_discovery_sweep_without_network_skips(db_session):
    rule = AutomationRule(name="sweep", kind="discovery_sweep", config={})
    db_session.add(rule)
    db_session.flush()
    result = automation.run_rule(db_session, rule)
    assert result["status"] == "skipped"
